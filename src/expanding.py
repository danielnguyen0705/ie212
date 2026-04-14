# src/expanding.py

import numpy as np
from sklearn.preprocessing import MinMaxScaler

from src.config import TARGET_IDX


def fit_and_scale_for_expanding_initial_window(raw_features_3d, first_test_t, initial_train_days):
    T, N, F = raw_features_3d.shape

    train_start_t = max(0, first_test_t - initial_train_days)
    train_end_t = first_test_t - 1

    scaled = np.zeros_like(raw_features_3d, dtype=np.float32)
    scalers = []
    close_mins = []
    close_maxs = []

    for j in range(N):
        scaler = MinMaxScaler()
        scaler.fit(raw_features_3d[train_start_t:train_end_t + 1, j, :])

        scaled[:, j, :] = scaler.transform(raw_features_3d[:, j, :]).astype(np.float32)
        scalers.append(scaler)

        close_mins.append(float(scaler.data_min_[TARGET_IDX]))
        close_maxs.append(float(scaler.data_max_[TARGET_IDX]))

    return scaled, scalers, np.array(close_mins), np.array(close_maxs), train_start_t, train_end_t 

def build_samples_for_target_range(close_only_3d, full_node_3d, adj_norm,
                                   start_t, end_t, lookback, dates, target_idx):
    X_seq_list = []
    X_node_list = []
    A_list = []
    y_res_list = []
    y_close_list = []
    last_close_list = []
    date_list = []

    for t in range(start_t, end_t + 1):
        if t - lookback < 0:
            continue

        seq = close_only_3d[t - lookback:t, :, :]
        seq = np.transpose(seq, (1, 0, 2))

        node_x = full_node_3d[t - 1, :, :]
        target_close = full_node_3d[t, :, target_idx]
        last_close = full_node_3d[t - 1, :, target_idx]
        target_res = target_close - last_close

        X_seq_list.append(seq.astype(np.float32))
        X_node_list.append(node_x.astype(np.float32))
        A_list.append(adj_norm.astype(np.float32))
        y_res_list.append(target_res.astype(np.float32))
        y_close_list.append(target_close.astype(np.float32))
        last_close_list.append(last_close.astype(np.float32))
        date_list.append(dates[t])

    X_seq = np.stack(X_seq_list)
    X_node = np.stack(X_node_list)
    A = np.stack(A_list)
    y_res = np.stack(y_res_list)
    y_close = np.stack(y_close_list)
    last_close = np.stack(last_close_list)
    date_list = np.array(date_list)

    return {
        "X_seq": X_seq,
        "X_node": X_node,
        "A": A,
        "y_res": y_res,
        "y_close": y_close,
        "last_close": last_close,
        "dates": date_list
    }

from src.dataset import StockGraphDataset


def pack_to_dataset(pack):
    return StockGraphDataset(
        X_seq=pack["X_seq"],
        X_node=pack["X_node"],
        A=pack["A"],
        y_res=pack["y_res"],
        y_close=pack["y_close"],
        last_close=pack["last_close"]
    )

from src.config import (
    EXP_TEST_DAYS,
    EXP_INITIAL_TRAIN_DAYS,
    TARGET_IDX,
)
from src.graph_builder import build_combined_graph_from_train_window


def prepare_expanding_step_data(
    test_t,
    lookback,
    val_days,
    dates,
    return_2d,
    close_only_3d,
    full_node_3d,
    tickers
):
    first_test_t = len(dates) - EXP_TEST_DAYS
    train_start_t = max(0, first_test_t - EXP_INITIAL_TRAIN_DAYS)
    train_end_t = test_t - 1

    adj_norm, adj_raw, corr_raw, graph_debug = build_combined_graph_from_train_window(
        return_2d=return_2d,
        tickers=tickers,
        train_start_t=train_start_t,
        train_end_t=train_end_t
    )

    sample_start_t = max(train_start_t + lookback, lookback)

    all_trainval = build_samples_for_target_range(
        close_only_3d=close_only_3d,
        full_node_3d=full_node_3d,
        adj_norm=adj_norm,
        start_t=sample_start_t,
        end_t=train_end_t,
        lookback=lookback,
        dates=dates,
        target_idx=TARGET_IDX
    )

    n_total = len(all_trainval["y_close"])
    if n_total <= val_days:
        raise ValueError("Không đủ train samples để tách validation.")

    split_idx = n_total - val_days

    train_pack = {
        k: v[:split_idx] if isinstance(v, np.ndarray) else v
        for k, v in all_trainval.items()
    }
    val_pack = {
        k: v[split_idx:] if isinstance(v, np.ndarray) else v
        for k, v in all_trainval.items()
    }

    test_pack = build_samples_for_target_range(
        close_only_3d=close_only_3d,
        full_node_3d=full_node_3d,
        adj_norm=adj_norm,
        start_t=test_t,
        end_t=test_t,
        lookback=lookback,
        dates=dates,
        target_idx=TARGET_IDX
    )

    meta = {
        "test_t": test_t,
        "test_date": dates[test_t],
        "train_start_t": train_start_t,
        "train_end_t": train_end_t,
        "adj_norm": adj_norm,
        "adj_raw": adj_raw,
        "corr_raw": corr_raw,
        "graph_debug": graph_debug
    }

    return train_pack, val_pack, test_pack, meta