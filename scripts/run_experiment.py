# scripts/run_experiment.py

import os
import random
import warnings
import copy

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
from src.artifacts import save_model_checkpoint, save_json, build_run_metadata

from src.config import (
    SEED,
    TICKERS,
    START_DATE,
    END_DATE,
    FEATURE_COLS,
    TARGET_IDX,
    LOOKBACK,
    DIRECTION_EPS,
    LSTM_HIDDEN,
    GNN_HIDDEN,
    MLP_HIDDEN,
    DROPOUT,
    EXP_WARM_START,
    EXP_TEST_DAYS,
    EXP_INITIAL_TRAIN_DAYS,
    EXP_VAL_DAYS,
    EXP_BATCH_SIZE,
    EXP_INIT_EPOCHS,
    EXP_UPDATE_EPOCHS,
    EXP_PATIENCE,
    EXP_LR_LSTM,
    EXP_LR_HYBRID,
)

from src.data_loader import load_all_tickers, align_common_index
from src.features import build_feature_tensor
from src.expanding import (
    fit_and_scale_for_expanding_initial_window,
    prepare_expanding_step_data,
    pack_to_dataset,
)
from src.models import LSTMOnlyModel, HybridLSTMGNNGraphGate
from src.train_eval import (
    compute_metrics,
    fit_model_silent,
    predict_model,
    predict_model_graph_gate,
)


warnings.filterwarnings("ignore")


def seed_everything(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def run_expanding_linear_backtest(
    dates,
    close_only_3d,
    full_node_3d,
    return_2d,
    test_days=None
):
    if test_days is None:
        test_days = EXP_TEST_DAYS

    T = len(dates)
    first_test_t = T - test_days

    preds_all = []
    trues_all = []
    lasts_all = []
    step_rows = []

    for step, test_t in enumerate(range(first_test_t, T), start=1):
        train_pack, val_pack, test_pack, meta = prepare_expanding_step_data(
            test_t=test_t,
            lookback=LOOKBACK,
            val_days=EXP_VAL_DAYS,
            dates=dates,
            return_2d=return_2d,
            close_only_3d=close_only_3d,
            full_node_3d=full_node_3d,
            tickers=TICKERS
        )

        X_train = train_pack["X_seq"].reshape(train_pack["X_seq"].shape[0], -1)
        y_train_res = train_pack["y_res"]

        X_test = test_pack["X_seq"].reshape(test_pack["X_seq"].shape[0], -1)
        y_test_close = test_pack["y_close"]
        last_close = test_pack["last_close"]

        lin_model = LinearRegression()
        lin_model.fit(X_train, y_train_res)

        pred_res = lin_model.predict(X_test)
        pred_close = last_close + pred_res

        day_mse = mean_squared_error(y_test_close.reshape(-1), pred_close.reshape(-1))

        preds_all.append(pred_close)
        trues_all.append(y_test_close)
        lasts_all.append(last_close)

        step_rows.append({
            "Step": step,
            "Date": meta["test_date"],
            "Day_MSE": day_mse
        })

        if step % 5 == 0 or step == 1 or step == test_days:
            print(f"[Linear] Step {step:02d}/{test_days} | Date={meta['test_date'].date()} | Day_MSE={day_mse:.6f}")

    preds_all = np.concatenate(preds_all, axis=0)
    trues_all = np.concatenate(trues_all, axis=0)
    lasts_all = np.concatenate(lasts_all, axis=0)

    metrics = compute_metrics(trues_all, preds_all, lasts_all, eps=DIRECTION_EPS)
    step_df = pd.DataFrame(step_rows)

    return metrics, step_df, preds_all, trues_all, lasts_all


def run_joint_expanding_lstm_hybrid_backtest(
    dates,
    close_only_3d,
    full_node_3d,
    return_2d,
    device,
    test_days=None
):
    if test_days is None:
        test_days = EXP_TEST_DAYS

    T = len(dates)
    first_test_t = T - test_days

    lstm_preds_all, lstm_trues_all, lstm_lasts_all = [], [], []
    hybrid_preds_all, hybrid_trues_all, hybrid_lasts_all = [], [], []

    lstm_rows = []
    hybrid_rows = []
    graph_rows = []
    gate_rows = []

    saved_lstm_state = None
    saved_hybrid_state = None

    for step, test_t in enumerate(range(first_test_t, T), start=1):
        train_pack, val_pack, test_pack, meta = prepare_expanding_step_data(
            test_t=test_t,
            lookback=LOOKBACK,
            val_days=EXP_VAL_DAYS,
            dates=dates,
            return_2d=return_2d,
            close_only_3d=close_only_3d,
            full_node_3d=full_node_3d,
            tickers=TICKERS
        )

        train_ds = pack_to_dataset(train_pack)
        val_ds = pack_to_dataset(val_pack)
        test_ds = pack_to_dataset(test_pack)

        train_loader = DataLoader(train_ds, batch_size=EXP_BATCH_SIZE, shuffle=True, num_workers=0)
        val_loader = DataLoader(val_ds, batch_size=EXP_BATCH_SIZE, shuffle=False, num_workers=0)
        test_loader = DataLoader(test_ds, batch_size=1, shuffle=False, num_workers=0)

        lstm_model = LSTMOnlyModel(
            input_dim=1,
            lstm_hidden=LSTM_HIDDEN,
            dropout=DROPOUT
        ).to(device)

        if EXP_WARM_START and saved_lstm_state is not None:
            lstm_model.load_state_dict(saved_lstm_state)

        current_epochs = EXP_INIT_EPOCHS if step == 1 else EXP_UPDATE_EPOCHS

        lstm_model, _ = fit_model_silent(
            model=lstm_model,
            train_loader=train_loader,
            val_loader=val_loader,
            epochs=current_epochs,
            lr=EXP_LR_LSTM,
            patience=EXP_PATIENCE,
            device=device,
            verbose=False
        )

        if EXP_WARM_START:
            saved_lstm_state = copy.deepcopy(lstm_model.state_dict())

        lstm_pred_close, true_close, last_close = predict_model(lstm_model, test_loader, device)
        lstm_day_mse = mean_squared_error(true_close.reshape(-1), lstm_pred_close.reshape(-1))

        lstm_preds_all.append(lstm_pred_close)
        lstm_trues_all.append(true_close)
        lstm_lasts_all.append(last_close)

        lstm_rows.append({
            "Step": step,
            "Date": meta["test_date"],
            "Day_MSE": lstm_day_mse
        })

        hybrid_model = HybridLSTMGNNGraphGate(
            seq_input_dim=1,
            node_input_dim=len(FEATURE_COLS),
            lstm_hidden=LSTM_HIDDEN,
            gnn_hidden=GNN_HIDDEN,
            mlp_hidden=MLP_HIDDEN,
            dropout=DROPOUT
        ).to(device)

        if EXP_WARM_START and saved_hybrid_state is not None:
            hybrid_model.load_state_dict(saved_hybrid_state)

        hybrid_model, _ = fit_model_silent(
            model=hybrid_model,
            train_loader=train_loader,
            val_loader=val_loader,
            epochs=current_epochs,
            lr=EXP_LR_HYBRID,
            patience=EXP_PATIENCE,
            device=device,
            verbose=False
        )

        if EXP_WARM_START:
            saved_hybrid_state = copy.deepcopy(hybrid_model.state_dict())

        hybrid_pred_close, hybrid_true_close, hybrid_last_close, hybrid_gate = predict_model_graph_gate(
            hybrid_model, test_loader, device
        )

        hybrid_day_mse = mean_squared_error(hybrid_true_close.reshape(-1), hybrid_pred_close.reshape(-1))

        hybrid_preds_all.append(hybrid_pred_close)
        hybrid_trues_all.append(hybrid_true_close)
        hybrid_lasts_all.append(hybrid_last_close)

        hybrid_rows.append({
            "Step": step,
            "Date": meta["test_date"],
            "Day_MSE": hybrid_day_mse
        })

        graph_rows.append({
            "Step": step,
            "Date": meta["test_date"],
            "Pearson_Edges": meta["graph_debug"]["pearson_edges"],
            "Assoc_Edges": meta["graph_debug"]["assoc_edges"],
            "Combined_Edges": meta["graph_debug"]["combined_edges"]
        })

        gate_rows.append({
            "Step": step,
            "Date": meta["test_date"],
            "Gate_Mean": float(hybrid_gate.mean()),
            "Gate_Min": float(hybrid_gate.min()),
            "Gate_Max": float(hybrid_gate.max()),
            "Gate_STD": float(hybrid_gate.std())
        })

        if step % 5 == 0 or step == 1 or step == test_days:
            print(
                f"Step {step:02d}/{test_days} | Date={meta['test_date'].date()} | "
                f"LSTM_MSE={lstm_day_mse:.6f} | HybridGate_MSE={hybrid_day_mse:.6f} | "
                f"GateMean={hybrid_gate.mean():.3f}"
            )

    lstm_preds_all = np.concatenate(lstm_preds_all, axis=0)
    lstm_trues_all = np.concatenate(lstm_trues_all, axis=0)
    lstm_lasts_all = np.concatenate(lstm_lasts_all, axis=0)

    hybrid_preds_all = np.concatenate(hybrid_preds_all, axis=0)
    hybrid_trues_all = np.concatenate(hybrid_trues_all, axis=0)
    hybrid_lasts_all = np.concatenate(hybrid_lasts_all, axis=0)

    lstm_metrics = compute_metrics(lstm_trues_all, lstm_preds_all, lstm_lasts_all, eps=DIRECTION_EPS)
    hybrid_metrics = compute_metrics(hybrid_trues_all, hybrid_preds_all, hybrid_lasts_all, eps=DIRECTION_EPS)

    lstm_step_df = pd.DataFrame(lstm_rows)
    hybrid_step_df = pd.DataFrame(hybrid_rows)
    graph_step_df = pd.DataFrame(graph_rows)
    gate_step_df = pd.DataFrame(gate_rows)

    return (
        lstm_metrics, lstm_step_df, lstm_preds_all, lstm_trues_all, lstm_lasts_all,
        hybrid_metrics, hybrid_step_df, hybrid_preds_all, hybrid_trues_all, hybrid_lasts_all,
        graph_step_df, gate_step_df, lstm_model, hybrid_model
    )


def main():
    seed_everything(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print("DEVICE:", device)
    print("SEED:", SEED)

    os.makedirs("outputs", exist_ok=True)

    # Mini mode trước để test end-to-end nhanh
    MINI_TEST_DAYS = EXP_TEST_DAYS

    print("\n=== LOAD DATA ===")
    data_dict = load_all_tickers(TICKERS, START_DATE, END_DATE)
    data_dict, common_index = align_common_index(data_dict, TICKERS)

    features_3d, close_2d, return_2d, dates = build_feature_tensor(
        data_dict=data_dict,
        tickers=TICKERS,
        feature_cols=FEATURE_COLS
    )

    first_test_t = len(dates) - EXP_TEST_DAYS

    scaled_features_3d, scalers, close_mins, close_maxs, train_start_t, train_end_t = (
        fit_and_scale_for_expanding_initial_window(
            features_3d,
            first_test_t=first_test_t,
            initial_train_days=EXP_INITIAL_TRAIN_DAYS
        )
    )

    close_only_3d = scaled_features_3d[:, :, TARGET_IDX:TARGET_IDX+1].copy()
    full_node_3d = scaled_features_3d.copy()

    print("features_3d:", features_3d.shape)
    print("scaled_features_3d:", scaled_features_3d.shape)

    print("\n=== RUN LINEAR ===")
    linear_exp_metrics, linear_exp_step_df, linear_exp_pred, linear_exp_true, linear_exp_last = (
        run_expanding_linear_backtest(
            dates=dates,
            close_only_3d=close_only_3d,
            full_node_3d=full_node_3d,
            return_2d=return_2d,
            test_days=MINI_TEST_DAYS
        )
    )

    print("\n=== RUN LSTM + HYBRID ===")
    (
        lstm_exp_metrics, lstm_exp_step_df, lstm_exp_pred, lstm_exp_true, lstm_exp_last,
        hybrid_exp_metrics, hybrid_exp_step_df, hybrid_exp_pred, hybrid_exp_true, hybrid_exp_last,
        graph_step_df, gate_step_df, lstm_model_final, hybrid_model_final
    ) = run_joint_expanding_lstm_hybrid_backtest(
        dates=dates,
        close_only_3d=close_only_3d,
        full_node_3d=full_node_3d,
        return_2d=return_2d,
        device=device,
        test_days=MINI_TEST_DAYS
    )

    exp_results_df = pd.DataFrame([
        {"Model": "Linear Regression (Expanding)", **linear_exp_metrics},
        {"Model": "LSTM (Expanding)", **lstm_exp_metrics},
        {"Model": "Hybrid LSTM-GNN Graph-Gated (Expanding)", **hybrid_exp_metrics},
    ]).sort_values("MSE").reset_index(drop=True)

    compare_step_df = lstm_exp_step_df.rename(columns={"Day_MSE": "LSTM_Day_MSE"}).merge(
        hybrid_exp_step_df.rename(columns={"Day_MSE": "Hybrid_Day_MSE"}),
        on=["Step", "Date"],
        how="inner"
    )

    compare_step_df["Hybrid_Better"] = compare_step_df["Hybrid_Day_MSE"] < compare_step_df["LSTM_Day_MSE"]
    compare_step_df["Improvement"] = compare_step_df["LSTM_Day_MSE"] - compare_step_df["Hybrid_Day_MSE"]

    stock_rows = []
    for j, ticker in enumerate(TICKERS):
        lstm_mse_j = mean_squared_error(lstm_exp_true[:, j], lstm_exp_pred[:, j])
        hybrid_mse_j = mean_squared_error(hybrid_exp_true[:, j], hybrid_exp_pred[:, j])
        linear_mse_j = mean_squared_error(linear_exp_true[:, j], linear_exp_pred[:, j])

        stock_rows.append({
            "Ticker": ticker,
            "LSTM_MSE": lstm_mse_j,
            "Hybrid_MSE": hybrid_mse_j,
            "Linear_MSE": linear_mse_j,
            "Hybrid_Better_Than_LSTM": hybrid_mse_j < lstm_mse_j,
            "Improvement_vs_LSTM": lstm_mse_j - hybrid_mse_j
        })

    stock_mse_df = pd.DataFrame(stock_rows).sort_values("Improvement_vs_LSTM", ascending=False).reset_index(drop=True)

    print("\n=== RESULTS SUMMARY ===")
    print(exp_results_df)

    print("\n=== COMPARE STEP DF ===")
    print(compare_step_df)

    print("\n=== STOCK MSE DF ===")
    print(stock_mse_df)

    exp_results_df.to_csv("outputs/exp_results_full.csv", index=False)
    compare_step_df.to_csv("outputs/compare_step_full.csv", index=False)
    stock_mse_df.to_csv("outputs/stock_mse_full.csv", index=False)
    graph_step_df.to_csv("outputs/graph_step_full.csv", index=False)
    gate_step_df.to_csv("outputs/gate_step_full.csv", index=False)

    os.makedirs("models", exist_ok=True)

    run_config = {
        "tickers": TICKERS,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "feature_cols": FEATURE_COLS,
        "lookback": LOOKBACK,
        "exp_test_days": EXP_TEST_DAYS,
        "exp_initial_train_days": EXP_INITIAL_TRAIN_DAYS,
        "exp_val_days": EXP_VAL_DAYS,
        "exp_batch_size": EXP_BATCH_SIZE,
        "exp_init_epochs": EXP_INIT_EPOCHS,
        "exp_update_epochs": EXP_UPDATE_EPOCHS,
        "exp_patience": EXP_PATIENCE,
        "exp_lr_lstm": EXP_LR_LSTM,
        "exp_lr_hybrid": EXP_LR_HYBRID,
        "lstm_hidden": LSTM_HIDDEN,
        "gnn_hidden": GNN_HIDDEN,
        "mlp_hidden": MLP_HIDDEN,
        "dropout": DROPOUT,
        "seed": SEED,
        "device": str(device),
    }

    summary_dict = {
        "linear_metrics": linear_exp_metrics,
        "lstm_metrics": lstm_exp_metrics,
        "hybrid_metrics": hybrid_exp_metrics,
    }

    save_model_checkpoint(
        lstm_model_final,
        "models/lstm_expanding_best_full.pt",
        extra={
            "model_name": "LSTMOnlyModel",
            "config": run_config,
            "metrics": lstm_exp_metrics,
        }
    )

    save_model_checkpoint(
        hybrid_model_final,
        "models/hybrid_expanding_best_full.pt",
        extra={
            "model_name": "HybridLSTMGNNGraphGate",
            "config": run_config,
            "metrics": hybrid_exp_metrics,
        }
    )

    metrics_json = {
        "linear_metrics": linear_exp_metrics,
        "lstm_metrics": lstm_exp_metrics,
        "hybrid_metrics": hybrid_exp_metrics,
    }
    save_json(metrics_json, "outputs/metrics_full.json")

    run_metadata = build_run_metadata(run_config, summary_dict)
    save_json(run_metadata, "models/run_metadata_full.json")

    print("\nSaved files:")
    print("- outputs/exp_results_full.csv")
    print("- outputs/compare_step_full.csv")
    print("- outputs/stock_mse_full.csv")
    print("- outputs/graph_step_full.csv")
    print("- outputs/gate_step_full.csv")

    print("- outputs/metrics_full.json")
    print("- models/lstm_expanding_best_full.pt")
    print("- models/hybrid_expanding_best_full.pt")
    print("- models/run_metadata_full.json")


if __name__ == "__main__":
    main()