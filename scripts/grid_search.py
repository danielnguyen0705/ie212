# scripts/grid_search.py

import os
import random
import warnings
import copy
import json
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader
from sklearn.metrics import mean_squared_error

import _path_setup
from src.config import (
    SEED, TICKERS, START_DATE, END_DATE, FEATURE_COLS, TARGET_IDX, LOOKBACK,
    LSTM_HIDDEN, GNN_HIDDEN, MLP_HIDDEN, DROPOUT, EXP_WARM_START,
    EXP_INITIAL_TRAIN_DAYS, EXP_VAL_DAYS, EXP_BATCH_SIZE,
    EXP_FAST_INIT_EPOCHS, EXP_FAST_UPDATE_EPOCHS, EXP_FAST_PATIENCE,
    EXP_LR_HYBRID, EXP_GAUSSIAN_NOISE_STD
)
from src.data_loader import load_all_tickers, align_common_index
from src.features import build_feature_tensor
from src.expanding import pack_to_dataset
from src.graph_builder import build_combined_graph_from_train_window
from src.models import TSNAttentionGraphGatedLSTMGNN
from src.train_eval import fit_model_silent, predict_model_with_attention
from src.rolling_scaler import RollingMinMaxScaler
from src.evaluation import compute_full_evaluation

warnings.filterwarnings("ignore")

def seed_everything(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

def prepare_step_data_rolling_scaler(
    test_t,
    lookback,
    val_days,
    dates,
    return_2d,
    raw_features_3d,
    tickers,
    window_size,
    pearson_threshold
):
    first_test_t = len(dates) - 15  # Rút ngắn còn 15 ngày để grid search chạy nhanh
    train_start_t = max(0, first_test_t - EXP_INITIAL_TRAIN_DAYS)
    train_end_t = test_t - 1

    # Khởi tạo Rolling MinMaxScaler dựa trên W
    T, N, F = raw_features_3d.shape
    step_scaled = np.zeros_like(raw_features_3d, dtype=np.float32)
    close_mins = np.zeros(N, dtype=np.float32)
    close_maxs = np.zeros(N, dtype=np.float32)

    for j in range(N):
        # fit scaler động trên W ngày gần nhất tính đến train_end_t
        scaler_w_start = max(0, train_end_t - window_size + 1)
        scaler_data = raw_features_3d[scaler_w_start:train_end_t + 1, j, :]
        
        feature_min = scaler_data.min(axis=0)
        feature_max = scaler_data.max(axis=0)
        feature_range = feature_max - feature_min + 1e-8
        
        step_scaled[:, j, :] = (raw_features_3d[:, j, :] - feature_min) / feature_range
        close_mins[j] = float(feature_min[TARGET_IDX])
        close_maxs[j] = float(feature_max[TARGET_IDX])

    step_close_only_3d = step_scaled.copy()
    step_full_node_3d = step_scaled.copy()

    # Tính toán đồ thị động với Pearson threshold tương ứng
    adj_norm, adj_raw, corr_raw, graph_debug = build_combined_graph_from_train_window(
        return_2d=return_2d,
        tickers=tickers,
        train_start_t=train_start_t,
        train_end_t=train_end_t
    )
    # Ghi đè Pearson threshold động nếu là "auto"
    if pearson_threshold == "auto":
        from src.graph_builder import normalize_adjacency, sparsify_keep_topk
        # pearson_raw từ train returns
        graph_start_t = max(train_start_t, train_end_t - 504 + 1)
        train_returns = return_2d[graph_start_t:train_end_t + 1].copy()
        corr = np.corrcoef(train_returns.T)
        corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        pearson_raw = np.abs(corr).astype(np.float32)
        triu_indices = np.triu_indices_from(pearson_raw, k=1)
        off_diag_vals = pearson_raw[triu_indices]
        if len(off_diag_vals) > 0:
            actual_threshold = float(np.percentile(off_diag_vals, 70))
        else:
            actual_threshold = 0.45
        
        from src.config import EXP_ASSOC_EDGE_WEIGHT, EXP_FINAL_GRAPH_TOPK
        pearson_raw[pearson_raw < actual_threshold] = 0.0
        np.fill_diagonal(pearson_raw, 1.0)
        
        # Build combined graph
        _, assoc_raw, _, _ = build_combined_graph_from_train_window(
            return_2d, tickers, train_start_t, train_end_t
        )
        combined_raw = np.maximum(pearson_raw, 0.50 * assoc_raw) # fallback to default weight
        combined_raw = sparsify_keep_topk(combined_raw, topk=EXP_FINAL_GRAPH_TOPK, keep_self=True)
        adj_norm = normalize_adjacency(combined_raw).astype(np.float32)

    sample_start_t = max(train_start_t + lookback, lookback)

    all_trainval = []
    for t in range(sample_start_t, train_end_t + 1):
        if t - lookback < 0:
            continue
        seq = step_close_only_3d[t - lookback:t, :, :]
        seq = np.transpose(seq, (1, 0, 2))
        node_x = step_full_node_3d[t - 1, :, :]
        target_close = step_full_node_3d[t, :, TARGET_IDX]
        last_close = step_full_node_3d[t - 1, :, TARGET_IDX]
        target_res = target_close - last_close

        all_trainval.append({
            "seq": seq.astype(np.float32),
            "node_x": node_x.astype(np.float32),
            "adj": adj_norm.astype(np.float32),
            "y_res": target_res.astype(np.float32),
            "y_close": target_close.astype(np.float32),
            "last_close": last_close.astype(np.float32),
        })

    n_total = len(all_trainval)
    split_idx = n_total - val_days

    train_pack = {
        "X_seq": np.stack([x["seq"] for x in all_trainval[:split_idx]]),
        "X_node": np.stack([x["node_x"] for x in all_trainval[:split_idx]]),
        "A": np.stack([x["adj"] for x in all_trainval[:split_idx]]),
        "y_res": np.stack([x["y_res"] for x in all_trainval[:split_idx]]),
        "y_close": np.stack([x["y_close"] for x in all_trainval[:split_idx]]),
        "last_close": np.stack([x["last_close"] for x in all_trainval[:split_idx]]),
    }

    val_pack = {
        "X_seq": np.stack([x["seq"] for x in all_trainval[split_idx:]]),
        "X_node": np.stack([x["node_x"] for x in all_trainval[split_idx:]]),
        "A": np.stack([x["adj"] for x in all_trainval[split_idx:]]),
        "y_res": np.stack([x["y_res"] for x in all_trainval[split_idx:]]),
        "y_close": np.stack([x["y_close"] for x in all_trainval[split_idx:]]),
        "last_close": np.stack([x["last_close"] for x in all_trainval[split_idx:]]),
    }

    # Test sample chỉ có 1
    t = test_t
    seq = step_close_only_3d[t - lookback:t, :, :]
    seq = np.transpose(seq, (1, 0, 2))
    node_x = step_full_node_3d[t - 1, :, :]
    target_close = step_full_node_3d[t, :, TARGET_IDX]
    last_close = step_full_node_3d[t - 1, :, TARGET_IDX]
    target_res = target_close - last_close

    test_pack = {
        "X_seq": np.expand_dims(seq.astype(np.float32), axis=0),
        "X_node": np.expand_dims(node_x.astype(np.float32), axis=0),
        "A": np.expand_dims(adj_norm.astype(np.float32), axis=0),
        "y_res": np.expand_dims(target_res.astype(np.float32), axis=0),
        "y_close": np.expand_dims(target_close.astype(np.float32), axis=0),
        "last_close": np.expand_dims(last_close.astype(np.float32), axis=0),
    }

    meta = {
        "test_date": dates[test_t],
        "close_mins": close_mins,
        "close_maxs": close_maxs,
    }

    return train_pack, val_pack, test_pack, meta

def run_grid_search_experiment(
    dates,
    raw_features_3d,
    return_2d,
    device,
    window_size,
    pearson_threshold,
    gate_type
):
    T = len(dates)
    test_days = 15
    first_test_t = T - test_days

    preds_all = []
    trues_all = []
    lasts_all = []

    saved_state = None
    num_all_features = len(FEATURE_COLS)

    for step, test_t in enumerate(range(first_test_t, T), start=1):
        train_pack, val_pack, test_pack, meta = prepare_step_data_rolling_scaler(
            test_t=test_t,
            lookback=LOOKBACK,
            val_days=EXP_VAL_DAYS,
            dates=dates,
            return_2d=return_2d,
            raw_features_3d=raw_features_3d,
            tickers=TICKERS,
            window_size=window_size,
            pearson_threshold=pearson_threshold
        )

        close_mins = meta["close_mins"]
        close_maxs = meta["close_maxs"]

        train_ds = pack_to_dataset(train_pack)
        val_ds = pack_to_dataset(val_pack)
        test_ds = pack_to_dataset(test_pack)

        train_loader = DataLoader(train_ds, batch_size=EXP_BATCH_SIZE, shuffle=True, num_workers=0)
        val_loader = DataLoader(val_ds, batch_size=EXP_BATCH_SIZE, shuffle=False, num_workers=0)
        test_loader = DataLoader(test_ds, batch_size=1, shuffle=False, num_workers=0)

        # TSN-Attention model with gate parameter
        model = TSNAttentionGraphGatedLSTMGNN(
            seq_input_dim=num_all_features,
            node_input_dim=num_all_features,
            lstm_hidden=LSTM_HIDDEN,
            gnn_hidden=GNN_HIDDEN,
            mlp_hidden=MLP_HIDDEN,
            dropout=DROPOUT,
            gate_type=gate_type
        ).to(device)

        if EXP_WARM_START and saved_state is not None:
            model.load_state_dict(saved_state)

        # Sử dụng ít epoch hơn để tối ưu thời gian chạy Grid Search (3 epochs cho fast update)
        current_epochs = 10 if step == 1 else 3
        model, _ = fit_model_silent(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            epochs=current_epochs,
            lr=EXP_LR_HYBRID,
            patience=EXP_FAST_PATIENCE,
            device=device,
            verbose=False,
            noise_std=EXP_GAUSSIAN_NOISE_STD
        )

        if EXP_WARM_START:
            saved_state = copy.deepcopy(model.state_dict())

        pred_close, trues, lasts, _, _ = predict_model_with_attention(model, test_loader, device)

        # Inverse scaling
        pred_close_real = pred_close * (close_maxs - close_mins)[None, :] + close_mins[None, :]
        trues_real = trues * (close_maxs - close_mins)[None, :] + close_mins[None, :]
        lasts_real = lasts * (close_maxs - close_mins)[None, :] + close_mins[None, :]

        preds_all.append(pred_close_real)
        trues_all.append(trues_real)
        lasts_all.append(lasts_real)

    preds_all = np.concatenate(preds_all, axis=0)
    trues_all = np.concatenate(trues_all, axis=0)
    lasts_all = np.concatenate(lasts_all, axis=0)

    # Đánh giá các chỉ số
    eval_metrics = compute_full_evaluation(
        y_true=trues_all,
        y_pred=preds_all,
        last_close=lasts_all,
        risk_free_rate=0.0,
        direction_eps=0.0
    )

    return eval_metrics

def main():
    seed_everything(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Running Grid Search on device: {device}")

    # Load data
    data_dict = load_all_tickers(TICKERS, START_DATE, END_DATE)
    data_dict, common_index = align_common_index(data_dict, TICKERS)
    features_3d, close_2d, return_2d, dates = build_feature_tensor(
        data_dict=data_dict,
        tickers=TICKERS,
        feature_cols=FEATURE_COLS
    )

    # Grid search parameters
    windows = [30, 60, 90]
    thresholds = [0.45, "auto"]
    gates = ["sigmoid", "tanh"]

    results = []

    os.makedirs("outputs/grid_search", exist_ok=True)

    for w in windows:
        for t in thresholds:
            for g in gates:
                print(f"\nEvaluating: W={w} | Threshold={t} | Gate={g} ...")
                try:
                    metrics = run_grid_search_experiment(
                        dates=dates,
                        raw_features_3d=features_3d,
                        return_2d=return_2d,
                        device=device,
                        window_size=w,
                        pearson_threshold=t,
                        gate_type=g
                    )
                    
                    results.append({
                        "window_size": w,
                        "pearson_threshold": t,
                        "gate_type": g,
                        "MSE": float(metrics["MSE"]),
                        "MAE": float(metrics["MAE"]),
                        "RMSE": float(metrics["RMSE"]),
                        "Directional_Accuracy": float(metrics["Directional_Accuracy"]),
                        "Sharpe_Ratio": float(metrics["Sharpe_Ratio"]),
                        "Max_Drawdown": float(metrics["Maximum_Drawdown"])
                    })
                    print(f"Result -> MSE: {metrics['MSE']:.4f} | DA: {metrics['Directional_Accuracy']:.2%} | Sharpe: {metrics['Sharpe_Ratio']:.2f}")
                except Exception as e:
                    print(f"Failed configuration W={w}, T={t}, G={g}. Error: {e}")

    results_df = pd.DataFrame(results)
    results_df.to_csv("outputs/grid_search/grid_search_results.csv", index=False)

    # Tìm ra cấu hình tối ưu nhất (ở đây ưu tiên Directional Accuracy và Sharpe Ratio để phục vụ chiến lược giao dịch)
    best_config = results_df.sort_values(by=["Directional_Accuracy", "Sharpe_Ratio"], ascending=[False, False]).iloc[0]
    print("\n" + "="*80)
    print("BEST CONFIGURATION FOUND:")
    print(best_config)
    print("="*80)

    with open("outputs/grid_search/best_config.json", "w", encoding="utf-8") as f:
        json.dump(best_config.to_dict(), f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
