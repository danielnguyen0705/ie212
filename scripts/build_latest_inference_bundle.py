import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.rolling_scaler import RollingMinMaxScaler
from src.config import (
    FEATURE_COLS, TARGET_COL, LOOKBACK,
    EXP_GRAPH_RECENT_DAYS, EXP_PEARSON_THRESHOLD, EXP_PEARSON_TOPK,
    EXP_ASSOC_RECENT_DAYS, EXP_ASSOC_MIN_SUPPORT, EXP_ASSOC_MIN_CONFIDENCE,
    EXP_ASSOC_LIFT_THRESHOLD, EXP_ASSOC_TOPK, EXP_ASSOC_EDGE_WEIGHT,
    EXP_FINAL_GRAPH_TOPK
)
from src.graph_builder import build_combined_graph_from_train_window

TARGET_IDX = FEATURE_COLS.index(TARGET_COL)


def read_one_csv(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    # chuẩn hóa cột ngày
    date_col = None
    for c in ["Date", "date", "Datetime", "datetime"]:
        if c in df.columns:
            date_col = c
            break

    if date_col is not None:
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.set_index(date_col)
    else:
        df.index = pd.to_datetime(df.index)

    keep_cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    df = df[keep_cols].copy()

    if "Close" not in df.columns:
        raise ValueError(f"{csv_path.name} không có cột Close")
    if "Volume" not in df.columns:
        df["Volume"] = 0.0

    df["Close"] = pd.to_numeric(df["Close"], errors="coerce").ffill()
    df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce").fillna(0.0)

    df["Return"] = df["Close"].pct_change().fillna(0.0)
    df["MA5"] = df["Close"].rolling(5).mean()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["Volatility5"] = df["Return"].rolling(5).std()
    df["Volatility20"] = df["Return"].rolling(20).std()

    df = df.dropna().copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        default="data/raw",
        help="Thư mục chứa các file csv theo ticker",
    )
    parser.add_argument(
        "--output",
        default="data/inference/latest_window.npz",
        help="File .npz output",
    )
    parser.add_argument(
        "--lookback",
        type=int,
        default=LOOKBACK,
        help="Số ngày lookback cho LSTM",
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=60,
        help="Số ngày cửa sổ trượt để fit scaler động",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    out_path = Path(args.output)

    if not data_dir.exists():
        raise FileNotFoundError(f"Data dir not found: {data_dir}")

    csv_files = sorted(data_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No csv files found in: {data_dir}")

    tickers = [p.stem for p in csv_files]
    print(f"Tickers ({len(tickers)}): {tickers}")

    data_dict = {}
    for p in csv_files:
        data_dict[p.stem] = read_one_csv(p)

    common_index = None
    for ticker in tickers:
        idx = data_dict[ticker].index
        common_index = idx if common_index is None else common_index.intersection(idx)

    common_index = common_index.sort_values()

    for ticker in tickers:
        data_dict[ticker] = data_dict[ticker].loc[common_index].copy()

    print(f"Common dates: {len(common_index)}")
    print(f"Date range: {common_index.min()} -> {common_index.max()}")

    if len(common_index) <= args.lookback:
        raise ValueError(
            f"Không đủ dữ liệu sau khi intersect ngày chung. "
            f"Need > {args.lookback}, got {len(common_index)}"
        )

    # 1. Build raw tensor
    full_node_3d = np.stack(
        [data_dict[t][FEATURE_COLS].values.astype(np.float32) for t in tickers],
        axis=1,  # [T, N, F]
    )

    # 2. Áp dụng Rolling MinMaxScaler
    # Để tránh data leakage, ta chỉ fit scaler trên cửa sổ trượt W ngày cuối cùng
    # (ngay trước thời điểm inference)
    scaler = RollingMinMaxScaler(window_size=args.window_size)
    scaled_node_3d = scaler.fit_transform(full_node_3d, close_idx=TARGET_IDX)

    # Tạo close_only_3d từ scaled node features
    scaled_close_only_3d = scaled_node_3d[:, :, TARGET_IDX:TARGET_IDX + 1]

    # Return không được scale (giữ nguyên để làm đồ thị, hoặc scale tùy ý)
    return_2d = np.stack(
        [data_dict[t]["Return"].values.astype(np.float32) for t in tickers],
        axis=1,  # [T, N]
    )

    t_last = len(common_index) - 1

    # Lấy seq 20 ngày cuối cùng: [N, T, 1]
    seq = scaled_close_only_3d[t_last - args.lookback + 1:t_last + 1, :, :]
    seq = np.transpose(seq, (1, 0, 2))

    node_x = scaled_node_3d[t_last, :, :]
    last_close = scaled_node_3d[t_last, :, TARGET_IDX]

    train_start_t = max(0, t_last - (252 * 2) + 1)
    train_end_t = t_last
    adj_norm, adj_raw, _, _ = build_combined_graph_from_train_window(
        return_2d=return_2d,
        tickers=tickers,
        train_start_t=train_start_t,
        train_end_t=train_end_t,
    )

    # save batch dimension
    x_seq = np.expand_dims(seq.astype(np.float32), axis=0)
    x_node = np.expand_dims(node_x.astype(np.float32), axis=0)
    A = np.expand_dims(adj_norm.astype(np.float32), axis=0)
    last_close = np.expand_dims(last_close.astype(np.float32), axis=0)

    # Lấy tham số scaler
    scaler_params = scaler.get_scaler_params()

    out_path.parent.mkdir(parents=True, exist_ok=True)

    np.savez(
        out_path,
        X_seq=x_seq,
        X_node=x_node,
        A=A,
        last_close=last_close,
        tickers=np.array(tickers, dtype=object),
        as_of_date=np.array(str(common_index[t_last].date()), dtype=object),
        adj_raw=adj_raw.astype(np.float32),
        feature_cols=np.array(FEATURE_COLS, dtype=object),
        **scaler_params
    )

    print("=" * 80)
    print(f"Saved inference bundle (with Rolling Scaler) to: {out_path}")
    print(f"as_of_date: {common_index[t_last].date()}")
    print(f"X_seq shape: {x_seq.shape}")
    print(f"X_node shape: {x_node.shape}")
    print(f"A shape: {A.shape}")
    print(f"last_close shape: {last_close.shape}")
    print("=" * 80)


if __name__ == "__main__":
    main()
