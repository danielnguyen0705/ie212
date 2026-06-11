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
import _path_setup
from src.artifacts import save_model_checkpoint, save_json, build_run_metadata

from src.config import (
    SEED,
    TICKERS,
    START_DATE,
    END_DATE,
    BASE_FEATURE_COLS,
    TSN_FEATURE_COLS,
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
    EXP_GAUSSIAN_NOISE_STD,
)

from src.data_loader import load_all_tickers, align_common_index
from src.features import build_feature_tensor
from src.expanding import (
    fit_and_scale_for_expanding_initial_window,
    prepare_expanding_step_data,
    pack_to_dataset,
)
from src.models import (
    LSTMOnlyModel,
    HybridLSTMGNNNoGate,
    HybridLSTMGNNGraphGate,
    TSNAttentionGraphGatedLSTMGNN,
)
from src.train_eval import (
    compute_metrics,
    fit_model_silent,
    predict_model,
    predict_model_graph_gate,
    predict_model_with_attention,
    initialize_hybrid_from_lstm_model,
    initialize_graph_gate_from_no_gate,
    initialize_tsn_from_graph_gate_model,
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
    no_gate_preds_all, no_gate_trues_all, no_gate_lasts_all = [], [], []
    graph_gate_preds_all, graph_gate_trues_all, graph_gate_lasts_all = [], [], []
    gg_tsn_preds_all, gg_tsn_trues_all, gg_tsn_lasts_all = [], [], []
    tsn_attn_preds_all, tsn_attn_trues_all, tsn_attn_lasts_all = [], [], []

    lstm_rows = []
    no_gate_rows = []
    graph_gate_rows = []
    gg_tsn_rows = []
    tsn_attn_rows = []

    graph_rows = []
    gate_rows = []

    saved_lstm_state = None
    saved_no_gate_state = None
    saved_graph_gate_state = None
    saved_gg_tsn_state = None
    saved_tsn_attn_state = None

    for step, test_t in enumerate(range(first_test_t, T), start=1):
        train_pack, val_pack, test_pack, meta = prepare_expanding_step_data(
            test_t=test_t,
            lookback=LOOKBACK,
            val_days=EXP_VAL_DAYS,
            dates=dates,
            return_2d=return_2d,
            close_only_3d=close_only_3d,
            full_node_3d=full_node_3d[:, :, :len(BASE_FEATURE_COLS)],
            tickers=TICKERS
        )

        train_ds = pack_to_dataset(train_pack)
        val_ds = pack_to_dataset(val_pack)
        test_ds = pack_to_dataset(test_pack)

        train_loader = DataLoader(train_ds, batch_size=EXP_BATCH_SIZE, shuffle=True, num_workers=0)
        val_loader = DataLoader(val_ds, batch_size=EXP_BATCH_SIZE, shuffle=False, num_workers=0)
        test_loader = DataLoader(test_ds, batch_size=1, shuffle=False, num_workers=0)

        current_epochs = EXP_INIT_EPOCHS if step == 1 else EXP_UPDATE_EPOCHS

        lstm_model = LSTMOnlyModel(
            input_dim=1,
            lstm_hidden=LSTM_HIDDEN,
            dropout=DROPOUT
        ).to(device)

        if EXP_WARM_START and saved_lstm_state is not None:
            lstm_model.load_state_dict(saved_lstm_state)

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

        no_gate_model = HybridLSTMGNNNoGate(
            seq_input_dim=1,
            node_input_dim=len(BASE_FEATURE_COLS),
            lstm_hidden=LSTM_HIDDEN,
            gnn_hidden=GNN_HIDDEN,
            mlp_hidden=MLP_HIDDEN,
            dropout=DROPOUT
        ).to(device)

        if EXP_WARM_START and saved_no_gate_state is not None:
            no_gate_model.load_state_dict(saved_no_gate_state)
        else:
            no_gate_model = initialize_hybrid_from_lstm_model(no_gate_model, lstm_model)

        no_gate_model, _ = fit_model_silent(
            model=no_gate_model,
            train_loader=train_loader,
            val_loader=val_loader,
            epochs=current_epochs,
            lr=EXP_LR_HYBRID,
            patience=EXP_PATIENCE,
            device=device,
            verbose=False
        )

        if EXP_WARM_START:
            saved_no_gate_state = copy.deepcopy(no_gate_model.state_dict())

        no_gate_pred_close, no_gate_true_close, no_gate_last_close, _ = predict_model_graph_gate(
            no_gate_model, test_loader, device
        )
        no_gate_day_mse = mean_squared_error(no_gate_true_close.reshape(-1), no_gate_pred_close.reshape(-1))

        no_gate_preds_all.append(no_gate_pred_close)
        no_gate_trues_all.append(no_gate_true_close)
        no_gate_lasts_all.append(no_gate_last_close)

        no_gate_rows.append({
            "Step": step,
            "Date": meta["test_date"],
            "Day_MSE": no_gate_day_mse
        })

        graph_gate_model = HybridLSTMGNNGraphGate(
            seq_input_dim=1,
            node_input_dim=len(BASE_FEATURE_COLS),
            lstm_hidden=LSTM_HIDDEN,
            gnn_hidden=GNN_HIDDEN,
            mlp_hidden=MLP_HIDDEN,
            dropout=DROPOUT
        ).to(device)

        if EXP_WARM_START and saved_graph_gate_state is not None:
            graph_gate_model.load_state_dict(saved_graph_gate_state)
        else:
            graph_gate_model = initialize_graph_gate_from_no_gate(graph_gate_model, no_gate_model)

        graph_gate_model, _ = fit_model_silent(
            model=graph_gate_model,
            train_loader=train_loader,
            val_loader=val_loader,
            epochs=current_epochs,
            lr=EXP_LR_HYBRID,
            patience=EXP_PATIENCE,
            device=device,
            verbose=False
        )

        if EXP_WARM_START:
            saved_graph_gate_state = copy.deepcopy(graph_gate_model.state_dict())

        graph_gate_pred_close, graph_gate_true_close, graph_gate_last_close, graph_gate_gate = predict_model_graph_gate(
            graph_gate_model, test_loader, device
        )
        graph_gate_day_mse = mean_squared_error(graph_gate_true_close.reshape(-1), graph_gate_pred_close.reshape(-1))

        graph_gate_preds_all.append(graph_gate_pred_close)
        graph_gate_trues_all.append(graph_gate_true_close)
        graph_gate_lasts_all.append(graph_gate_last_close)

        graph_gate_rows.append({
            "Step": step,
            "Date": meta["test_date"],
            "Day_MSE": graph_gate_day_mse
        })

        train_pack_tsn, val_pack_tsn, test_pack_tsn, meta_tsn = prepare_expanding_step_data(
            test_t=test_t,
            lookback=LOOKBACK,
            val_days=EXP_VAL_DAYS,
            dates=dates,
            return_2d=return_2d,
            close_only_3d=full_node_3d,
            full_node_3d=full_node_3d,
            tickers=TICKERS
        )

        train_ds_tsn = pack_to_dataset(train_pack_tsn)
        val_ds_tsn = pack_to_dataset(val_pack_tsn)
        test_ds_tsn = pack_to_dataset(test_pack_tsn)

        train_loader_tsn = DataLoader(train_ds_tsn, batch_size=EXP_BATCH_SIZE, shuffle=True, num_workers=0)
        val_loader_tsn = DataLoader(val_ds_tsn, batch_size=EXP_BATCH_SIZE, shuffle=False, num_workers=0)
        test_loader_tsn = DataLoader(test_ds_tsn, batch_size=1, shuffle=False, num_workers=0)

        num_all_features = len(FEATURE_COLS)

        gg_tsn_model = HybridLSTMGNNGraphGate(
            seq_input_dim=num_all_features,
            node_input_dim=num_all_features,
            lstm_hidden=LSTM_HIDDEN,
            gnn_hidden=GNN_HIDDEN,
            mlp_hidden=MLP_HIDDEN,
            dropout=DROPOUT
        ).to(device)

        if EXP_WARM_START and saved_gg_tsn_state is not None:
            gg_tsn_model.load_state_dict(saved_gg_tsn_state)

        gg_tsn_model, _ = fit_model_silent(
            model=gg_tsn_model,
            train_loader=train_loader_tsn,
            val_loader=val_loader_tsn,
            epochs=current_epochs,
            lr=EXP_LR_HYBRID,
            patience=EXP_PATIENCE,
            device=device,
            verbose=False
        )

        if EXP_WARM_START:
            saved_gg_tsn_state = copy.deepcopy(gg_tsn_model.state_dict())

        gg_tsn_pred_close, gg_tsn_true_close, gg_tsn_last_close, gg_tsn_gate = predict_model_graph_gate(
            gg_tsn_model, test_loader_tsn, device
        )
        gg_tsn_day_mse = mean_squared_error(gg_tsn_true_close.reshape(-1), gg_tsn_pred_close.reshape(-1))

        gg_tsn_preds_all.append(gg_tsn_pred_close)
        gg_tsn_trues_all.append(gg_tsn_true_close)
        gg_tsn_lasts_all.append(gg_tsn_last_close)

        gg_tsn_rows.append({
            "Step": step,
            "Date": meta["test_date"],
            "Day_MSE": gg_tsn_day_mse
        })

        tsn_attn_model = TSNAttentionGraphGatedLSTMGNN(
            seq_input_dim=num_all_features,
            node_input_dim=num_all_features,
            lstm_hidden=LSTM_HIDDEN,
            gnn_hidden=GNN_HIDDEN,
            mlp_hidden=MLP_HIDDEN,
            dropout=DROPOUT
        ).to(device)

        if EXP_WARM_START and saved_tsn_attn_state is not None:
            tsn_attn_model.load_state_dict(saved_tsn_attn_state)
        else:
            tsn_attn_model = initialize_tsn_from_graph_gate_model(tsn_attn_model, gg_tsn_model)

        tsn_attn_model, _ = fit_model_silent(
            model=tsn_attn_model,
            train_loader=train_loader_tsn,
            val_loader=val_loader_tsn,
            epochs=current_epochs,
            lr=EXP_LR_HYBRID,
            patience=EXP_PATIENCE,
            device=device,
            verbose=False,
            noise_std=EXP_GAUSSIAN_NOISE_STD
        )

        if EXP_WARM_START:
            saved_tsn_attn_state = copy.deepcopy(tsn_attn_model.state_dict())

        tsn_attn_pred_close, tsn_attn_true_close, tsn_attn_last_close, tsn_attn_gate, _ = predict_model_with_attention(
            tsn_attn_model, test_loader_tsn, device
        )
        tsn_attn_day_mse = mean_squared_error(tsn_attn_true_close.reshape(-1), tsn_attn_pred_close.reshape(-1))

        tsn_attn_preds_all.append(tsn_attn_pred_close)
        tsn_attn_trues_all.append(tsn_attn_true_close)
        tsn_attn_lasts_all.append(tsn_attn_last_close)

        tsn_attn_rows.append({
            "Step": step,
            "Date": meta["test_date"],
            "Day_MSE": tsn_attn_day_mse
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
            "Gate_Mean": float(graph_gate_gate.mean()),
            "Gate_Min": float(graph_gate_gate.min()),
            "Gate_Max": float(graph_gate_gate.max()),
            "Gate_STD": float(graph_gate_gate.std())
        })

        if step % 5 == 0 or step == 1 or step == test_days:
            print(
                f"Step {step:02d}/{test_days} | Date={meta['test_date'].date()} | "
                f"LSTM_MSE={lstm_day_mse:.6f} | GraphGate_MSE={graph_gate_day_mse:.6f} | "
                f"TSNAttn_MSE={tsn_attn_day_mse:.6f}"
            )

    lstm_preds_all = np.concatenate(lstm_preds_all, axis=0)
    lstm_trues_all = np.concatenate(lstm_trues_all, axis=0)
    lstm_lasts_all = np.concatenate(lstm_lasts_all, axis=0)

    no_gate_preds_all = np.concatenate(no_gate_preds_all, axis=0)
    no_gate_trues_all = np.concatenate(no_gate_trues_all, axis=0)
    no_gate_lasts_all = np.concatenate(no_gate_lasts_all, axis=0)

    graph_gate_preds_all = np.concatenate(graph_gate_preds_all, axis=0)
    graph_gate_trues_all = np.concatenate(graph_gate_trues_all, axis=0)
    graph_gate_lasts_all = np.concatenate(graph_gate_lasts_all, axis=0)

    gg_tsn_preds_all = np.concatenate(gg_tsn_preds_all, axis=0)
    gg_tsn_trues_all = np.concatenate(gg_tsn_trues_all, axis=0)
    gg_tsn_lasts_all = np.concatenate(gg_tsn_lasts_all, axis=0)

    tsn_attn_preds_all = np.concatenate(tsn_attn_preds_all, axis=0)
    tsn_attn_trues_all = np.concatenate(tsn_attn_trues_all, axis=0)
    tsn_attn_lasts_all = np.concatenate(tsn_attn_lasts_all, axis=0)

    lstm_metrics = compute_metrics(lstm_trues_all, lstm_preds_all, lstm_lasts_all, eps=DIRECTION_EPS)
    no_gate_metrics = compute_metrics(no_gate_trues_all, no_gate_preds_all, no_gate_lasts_all, eps=DIRECTION_EPS)
    graph_gate_metrics = compute_metrics(graph_gate_trues_all, graph_gate_preds_all, graph_gate_lasts_all, eps=DIRECTION_EPS)
    gg_tsn_metrics = compute_metrics(gg_tsn_trues_all, gg_tsn_preds_all, gg_tsn_lasts_all, eps=DIRECTION_EPS)
    tsn_attn_metrics = compute_metrics(tsn_attn_trues_all, tsn_attn_preds_all, tsn_attn_lasts_all, eps=DIRECTION_EPS)

    from src.evaluation import format_evaluation_report
    print("\n=== TSN-Attention Graph-Gated LSTM-GNN Evaluation ===")
    print(format_evaluation_report(tsn_attn_metrics))

    lstm_step_df = pd.DataFrame(lstm_rows)
    no_gate_step_df = pd.DataFrame(no_gate_rows)
    graph_gate_step_df = pd.DataFrame(graph_gate_rows)
    gg_tsn_step_df = pd.DataFrame(gg_tsn_rows)
    tsn_attn_step_df = pd.DataFrame(tsn_attn_rows)
    graph_step_df = pd.DataFrame(graph_rows)
    gate_step_df = pd.DataFrame(gate_rows)

    return (
        lstm_metrics, lstm_step_df, lstm_preds_all, lstm_trues_all, lstm_lasts_all,
        no_gate_metrics, no_gate_step_df, no_gate_preds_all, no_gate_trues_all, no_gate_lasts_all,
        graph_gate_metrics, graph_gate_step_df, graph_gate_preds_all, graph_gate_trues_all, graph_gate_lasts_all,
        gg_tsn_metrics, gg_tsn_step_df, gg_tsn_preds_all, gg_tsn_trues_all, gg_tsn_lasts_all,
        tsn_attn_metrics, tsn_attn_step_df, tsn_attn_preds_all, tsn_attn_trues_all, tsn_attn_lasts_all,
        graph_step_df, gate_step_df, lstm_model, no_gate_model, graph_gate_model, gg_tsn_model, tsn_attn_model
    )


def main():
    seed_everything(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print("DEVICE:", device)
    print("SEED:", SEED)

    os.makedirs("outputs", exist_ok=True)

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

    print("\n=== RUN DEEP LEARNING MODELS ===")
    (
        lstm_exp_metrics, lstm_exp_step_df, lstm_exp_pred, lstm_exp_true, lstm_exp_last,
        no_gate_exp_metrics, no_gate_exp_step_df, no_gate_exp_pred, no_gate_exp_true, no_gate_exp_last,
        graph_gate_exp_metrics, graph_gate_exp_step_df, graph_gate_exp_pred, graph_gate_exp_true, graph_gate_exp_last,
        gg_tsn_exp_metrics, gg_tsn_exp_step_df, gg_tsn_exp_pred, gg_tsn_exp_true, gg_tsn_exp_last,
        tsn_attn_exp_metrics, tsn_attn_exp_step_df, tsn_attn_exp_pred, tsn_attn_exp_true, tsn_attn_exp_last,
        graph_step_df, gate_step_df,
        lstm_model_final, no_gate_model_final, graph_gate_model_final, gg_tsn_model_final, tsn_attn_model_final
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
        {"Model": "LSTM-GNN No-Gate (Expanding)", **no_gate_exp_metrics},
        {"Model": "LSTM-GNN Graph-Gated (Expanding)", **graph_gate_exp_metrics},
        {"Model": "LSTM-GNN Graph-Gated + TSN Features (Expanding)", **gg_tsn_exp_metrics},
        {"Model": "TSN-Attention Graph-Gated LSTM-GNN (Expanding)", **tsn_attn_exp_metrics},
    ]).sort_values("MSE").reset_index(drop=True)

    compare_step_df = lstm_exp_step_df.rename(columns={"Day_MSE": "LSTM_Day_MSE"}).merge(
        graph_gate_exp_step_df.rename(columns={"Day_MSE": "GraphGate_Day_MSE"}),
        on=["Step", "Date"],
        how="inner"
    ).merge(
        tsn_attn_exp_step_df.rename(columns={"Day_MSE": "TSNAttn_Day_MSE"}),
        on=["Step", "Date"],
        how="inner"
    )

    compare_step_df["TSNAttn_Better_Than_LSTM"] = compare_step_df["TSNAttn_Day_MSE"] < compare_step_df["LSTM_Day_MSE"]
    compare_step_df["Improvement"] = compare_step_df["LSTM_Day_MSE"] - compare_step_df["TSNAttn_Day_MSE"]

    stock_rows = []
    for j, ticker in enumerate(TICKERS):
        lstm_mse_j = mean_squared_error(lstm_exp_true[:, j], lstm_exp_pred[:, j])
        graph_gate_mse_j = mean_squared_error(graph_gate_exp_true[:, j], graph_gate_exp_pred[:, j])
        tsn_attn_mse_j = mean_squared_error(tsn_attn_exp_true[:, j], tsn_attn_exp_pred[:, j])
        linear_mse_j = mean_squared_error(linear_exp_true[:, j], linear_exp_pred[:, j])

        stock_rows.append({
            "Ticker": ticker,
            "LSTM_MSE": lstm_mse_j,
            "GraphGate_MSE": graph_gate_mse_j,
            "TSNAttn_MSE": tsn_attn_mse_j,
            "Linear_MSE": linear_mse_j,
            "TSNAttn_Better_Than_LSTM": tsn_attn_mse_j < lstm_mse_j,
            "Improvement_vs_LSTM": lstm_mse_j - tsn_attn_mse_j
        })

    stock_mse_df = pd.DataFrame(stock_rows).sort_values("Improvement_vs_LSTM", ascending=False).reset_index(drop=True)

    print("\n=== RESULTS SUMMARY ===")
    print(exp_results_df)

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
        "no_gate_metrics": no_gate_exp_metrics,
        "graph_gate_metrics": graph_gate_exp_metrics,
        "gg_tsn_metrics": gg_tsn_exp_metrics,
        "tsn_attn_metrics": tsn_attn_exp_metrics,
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
        no_gate_model_final,
        "models/no_gate_expanding_best_full.pt",
        extra={
            "model_name": "HybridLSTMGNNNoGate",
            "config": run_config,
            "metrics": no_gate_exp_metrics,
        }
    )

    save_model_checkpoint(
        graph_gate_model_final,
        "models/hybrid_expanding_best_full.pt",
        extra={
            "model_name": "HybridLSTMGNNGraphGate",
            "config": run_config,
            "metrics": graph_gate_exp_metrics,
        }
    )

    save_model_checkpoint(
        gg_tsn_model_final,
        "models/gg_tsn_expanding_best_full.pt",
        extra={
            "model_name": "HybridLSTMGNNGraphGate_TSN",
            "config": run_config,
            "metrics": gg_tsn_exp_metrics,
        }
    )

    save_model_checkpoint(
        tsn_attn_model_final,
        "models/tsn_attn_expanding_best_full.pt",
        extra={
            "model_name": "TSNAttentionGraphGatedLSTMGNN",
            "config": run_config,
            "metrics": tsn_attn_exp_metrics,
        }
    )

    save_json(summary_dict, "outputs/metrics_full.json")

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
    print("- models/no_gate_expanding_best_full.pt")
    print("- models/hybrid_expanding_best_full.pt")
    print("- models/gg_tsn_expanding_best_full.pt")
    print("- models/tsn_attn_expanding_best_full.pt")
    print("- models/run_metadata_full.json")


if __name__ == "__main__":
    main()
