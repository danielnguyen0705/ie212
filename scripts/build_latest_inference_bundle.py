import argparse
from pathlib import Path

import numpy as np
import pandas as pd


FEATURE_COLS = [
    "Close",
    "Volume",
    "Return",
    "MA5",
    "MA20",
    "Volatility5",
    "Volatility20",
]
TARGET_COL = "Close"
TARGET_IDX = FEATURE_COLS.index(TARGET_COL)

LOOKBACK = 20

EXP_GRAPH_RECENT_DAYS = 252 * 2
EXP_PEARSON_THRESHOLD = 0.70
EXP_PEARSON_TOPK = 5

EXP_ASSOC_RECENT_DAYS = 252 * 2
EXP_ASSOC_MIN_SUPPORT = 0.05
EXP_ASSOC_MIN_CONFIDENCE = 0.10
EXP_ASSOC_LIFT_THRESHOLD = 1.50
EXP_ASSOC_TOPK = 3

EXP_ASSOC_EDGE_WEIGHT = 0.50
EXP_FINAL_GRAPH_TOPK = 4


def normalize_adjacency(adj: np.ndarray) -> np.ndarray:
    adj = adj.astype(np.float32)
    deg = adj.sum(axis=1)
    deg_inv_sqrt = np.power(np.maximum(deg, 1e-8), -0.5)
    d_inv_sqrt = np.diag(deg_inv_sqrt)
    adj_norm = d_inv_sqrt @ adj @ d_inv_sqrt
    return adj_norm.astype(np.float32)


def sparsify_keep_topk(weight_mat: np.ndarray, topk: int, keep_self: bool = True) -> np.ndarray:
    n = weight_mat.shape[0]
    out = np.zeros_like(weight_mat, dtype=np.float32)

    for i in range(n):
        row = weight_mat[i].copy()
        row[i] = 0.0

        pos_idx = np.where(row > 0)[0]
        if len(pos_idx) > 0:
            chosen = pos_idx[np.argsort(row[pos_idx])[::-1][:topk]]
            out[i, chosen] = row[chosen]

    out = np.maximum(out, out.T)

    if keep_self:
        np.fill_diagonal(out, 1.0)

    return out.astype(np.float32)


def build_sparse_pearson_graph_from_train_window(
    return_2d: np.ndarray,
    train_start_t: int,
    train_end_t: int,
    recent_days: int = EXP_GRAPH_RECENT_DAYS,
    threshold: float = EXP_PEARSON_THRESHOLD,
    topk: int = EXP_PEARSON_TOPK,
):
    graph_start_t = max(train_start_t, train_end_t - recent_days + 1)
    train_returns = return_2d[graph_start_t:train_end_t + 1].copy()

    corr = np.corrcoef(train_returns.T)
    corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)

    pearson_raw = np.abs(corr).astype(np.float32)
    pearson_raw[pearson_raw < threshold] = 0.0
    np.fill_diagonal(pearson_raw, 1.0)

    pearson_raw = sparsify_keep_topk(pearson_raw, topk=topk, keep_self=True)
    return pearson_raw, corr


def build_manual_association_graph_from_train_window(
    return_2d: np.ndarray,
    train_start_t: int,
    train_end_t: int,
    recent_days: int = EXP_ASSOC_RECENT_DAYS,
    min_support: float = EXP_ASSOC_MIN_SUPPORT,
    min_confidence: float = EXP_ASSOC_MIN_CONFIDENCE,
    lift_threshold: float = EXP_ASSOC_LIFT_THRESHOLD,
    topk: int = EXP_ASSOC_TOPK,
):
    graph_start_t = max(train_start_t, train_end_t - recent_days + 1)
    train_returns = return_2d[graph_start_t:train_end_t + 1].copy()

    up = (train_returns > 0).astype(np.float32)
    down = (train_returns < 0).astype(np.float32)

    _, n = up.shape
    assoc_raw = np.zeros((n, n), dtype=np.float32)

    p_up = up.mean(axis=0)
    p_down = down.mean(axis=0)

    for i in range(n):
        for j in range(n):
            if i == j:
                continue

            both_up = (up[:, i] * up[:, j]).mean()
            conf_up = both_up / (p_up[i] + 1e-8)
            lift_up = both_up / ((p_up[i] * p_up[j]) + 1e-8)

            both_down = (down[:, i] * down[:, j]).mean()
            conf_down = both_down / (p_down[i] + 1e-8)
            lift_down = both_down / ((p_down[i] * p_down[j]) + 1e-8)

            support = max(both_up, both_down)
            confidence = max(conf_up, conf_down)
            lift = max(lift_up, lift_down)

            if support >= min_support and confidence >= min_confidence and lift >= lift_threshold:
                assoc_raw[i, j] = max(assoc_raw[i, j], float(lift))

    max_val = assoc_raw.max()
    if max_val > 0:
        assoc_raw = assoc_raw / max_val

    np.fill_diagonal(assoc_raw, 1.0)
    assoc_raw = sparsify_keep_topk(assoc_raw, topk=topk, keep_self=True)
    return assoc_raw.astype(np.float32)


def build_combined_graph_from_train_window(
    return_2d: np.ndarray,
    train_start_t: int,
    train_end_t: int,
):
    pearson_raw, _ = build_sparse_pearson_graph_from_train_window(
        return_2d=return_2d,
        train_start_t=train_start_t,
        train_end_t=train_end_t,
    )

    assoc_raw = build_manual_association_graph_from_train_window(
        return_2d=return_2d,
        train_start_t=train_start_t,
        train_end_t=train_end_t,
    )

    combined_raw = np.maximum(pearson_raw, EXP_ASSOC_EDGE_WEIGHT * assoc_raw)
    combined_raw = sparsify_keep_topk(combined_raw, topk=EXP_FINAL_GRAPH_TOPK, keep_self=True)

    adj_norm = normalize_adjacency(combined_raw).astype(np.float32)
    return adj_norm, combined_raw


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
        # fallback: thử dùng index hiện tại
        df.index = pd.to_datetime(df.index)

    # giữ các cột cần
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

    # lấy giao ngày chung
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

    # build tensor
    full_node_3d = np.stack(
        [data_dict[t][FEATURE_COLS].values.astype(np.float32) for t in tickers],
        axis=1,  # [T, N, F]
    )

    close_only_3d = np.stack(
        [data_dict[t][["Close"]].values.astype(np.float32) for t in tickers],
        axis=1,  # [T, N, 1]
    )

    return_2d = np.stack(
        [data_dict[t]["Return"].values.astype(np.float32) for t in tickers],
        axis=1,  # [T, N]
    )

    t_last = len(common_index) - 1

    # inference cho bước kế tiếp sau ngày cuối cùng
    seq = close_only_3d[t_last - args.lookback + 1:t_last + 1, :, :]  # [lookback, N, 1]
    seq = np.transpose(seq, (1, 0, 2))  # [N, lookback, 1]

    node_x = full_node_3d[t_last, :, :]      # [N, 7]
    last_close = full_node_3d[t_last, :, TARGET_IDX]  # [N]

    train_start_t = max(0, t_last - (252 * 2) + 1)
    train_end_t = t_last

    adj_norm, adj_raw = build_combined_graph_from_train_window(
        return_2d=return_2d,
        train_start_t=train_start_t,
        train_end_t=train_end_t,
    )

    # save batch dimension
    x_seq = np.expand_dims(seq.astype(np.float32), axis=0)         # [1, N, T, 1]
    x_node = np.expand_dims(node_x.astype(np.float32), axis=0)     # [1, N, 7]
    A = np.expand_dims(adj_norm.astype(np.float32), axis=0)        # [1, N, N]
    last_close = np.expand_dims(last_close.astype(np.float32), axis=0)  # [1, N]

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
    )

    print("=" * 80)
    print(f"Saved inference bundle to: {out_path}")
    print(f"as_of_date: {common_index[t_last].date()}")
    print(f"X_seq shape: {x_seq.shape}")
    print(f"X_node shape: {x_node.shape}")
    print(f"A shape: {A.shape}")
    print(f"last_close shape: {last_close.shape}")
    print("=" * 80)


if __name__ == "__main__":
    main()