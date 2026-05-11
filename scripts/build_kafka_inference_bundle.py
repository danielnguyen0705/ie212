import argparse
import tempfile
from pathlib import Path

import boto3
from botocore.client import Config
import numpy as np
import pandas as pd

try:
    from scripts import _path_setup  # type: ignore
except ImportError:
    import _path_setup  # type: ignore

from scripts.build_latest_inference_bundle import (
    FEATURE_COLS,
    LOOKBACK,
    TARGET_IDX,
    build_combined_graph_from_train_window,
)


def create_s3_client(endpoint: str, access_key: str, secret_key: str):
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def list_and_download_parquet_files(
    *,
    endpoint: str,
    access_key: str,
    secret_key: str,
    bucket: str,
    prefix: str,
) -> pd.DataFrame:
    client = create_s3_client(endpoint, access_key, secret_key)

    parquet_keys: list[str] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix.rstrip("/") + "/"):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".parquet"):
                parquet_keys.append(key)

    if not parquet_keys:
        raise ValueError(f"No parquet files found in MinIO at s3://{bucket}/{prefix}")

    frames: list[pd.DataFrame] = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_root = Path(tmp_dir)
        for key in sorted(parquet_keys):
            local_path = tmp_root / Path(key).name
            client.download_file(bucket, key, str(local_path))
            frame = pd.read_parquet(local_path)
            frames.append(frame)
            print(f"[download] s3://{bucket}/{key} -> {local_path}")

    out = pd.concat(frames, axis=0, ignore_index=True)
    if out.empty:
        raise ValueError("Downloaded parquet files from MinIO but no rows were found.")
    return out


def load_raw_price_csv(csv_path: Path, ticker: str) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"Raw CSV not found for ticker {ticker}: {csv_path}")

    df = pd.read_csv(csv_path)

    date_col = None
    for candidate in ["Date", "date", "Datetime", "datetime"]:
        if candidate in df.columns:
            date_col = candidate
            break

    if date_col is not None:
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.set_index(date_col)
    else:
        df.index = pd.to_datetime(df.index)

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col not in df.columns:
            if col == "Volume":
                df[col] = 0.0
            elif col == "Close":
                raise ValueError(f"CSV for {ticker} missing required Close column")
            else:
                df[col] = df["Close"]

    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Close"] = df["Close"].ffill()
    for col in ["Open", "High", "Low"]:
        df[col] = df[col].fillna(df["Close"]).ffill()
    df["Volume"] = df["Volume"].fillna(0.0)

    df = df.dropna(subset=["Close"]).copy()
    df.index = pd.to_datetime(df.index).normalize()
    df = df.sort_index()
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["Return"] = out["Close"].pct_change().fillna(0.0)
    out["MA5"] = out["Close"].rolling(5).mean()
    out["MA20"] = out["Close"].rolling(20).mean()
    out["Volatility5"] = out["Return"].rolling(5).std()
    out["Volatility20"] = out["Return"].rolling(20).std()
    out = out.dropna().copy()
    out.index = pd.to_datetime(out.index)
    out = out.sort_index()
    return out


def latest_ticks_from_parquet(df: pd.DataFrame) -> list[tuple[str, float, pd.Timestamp]]:
    required_cols = {"symbol", "price", "event_time", "kafka_offset"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"MinIO parquet data missing required columns: {sorted(missing)}")

    out = df.copy()
    out["event_time"] = pd.to_datetime(out["event_time"], utc=True, errors="coerce")
    out["kafka_offset"] = pd.to_numeric(out["kafka_offset"], errors="coerce").fillna(-1)
    out = out.dropna(subset=["symbol", "price", "event_time"]).copy()
    out = out.sort_values(["symbol", "event_time", "kafka_offset"], ascending=[True, False, False])
    out = out.drop_duplicates(subset=["symbol"], keep="first")

    rows = [
        (str(row["symbol"]), float(row["price"]), pd.Timestamp(row["event_time"]))
        for _, row in out.iterrows()
    ]
    if not rows:
        raise ValueError("No usable latest ticks found in MinIO parquet data.")
    return rows


def merge_kafka_tick_into_history(
    raw_df: pd.DataFrame,
    kafka_price: float,
    event_time: pd.Timestamp,
) -> pd.DataFrame:
    out = raw_df.copy()
    event_date = pd.Timestamp(event_time).tz_localize(None).normalize()
    last_date = out.index.max()
    last_volume = float(out.iloc[-1]["Volume"]) if len(out) > 0 else 0.0

    new_row = pd.DataFrame(
        {
            "Open": [kafka_price],
            "High": [kafka_price],
            "Low": [kafka_price],
            "Close": [kafka_price],
            "Volume": [last_volume],
        },
        index=pd.DatetimeIndex([event_date]),
    )

    if event_date in out.index:
        out.loc[event_date, ["Open", "High", "Low", "Close"]] = kafka_price
        if pd.isna(out.loc[event_date, "Volume"]):
            out.loc[event_date, "Volume"] = last_volume
    elif event_date > last_date:
        out = pd.concat([out, new_row], axis=0)
    else:
        out.loc[last_date, ["Open", "High", "Low", "Close"]] = kafka_price

    out = out.sort_index()
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/raw", help="Directory containing raw CSV files")
    parser.add_argument("--output", default="data/inference/kafka_latest_window.npz", help="Output npz bundle")
    parser.add_argument("--lookback", type=int, default=LOOKBACK, help="Model lookback window")
    parser.add_argument("--minio-endpoint", required=True, help="MinIO endpoint URL")
    parser.add_argument("--minio-access-key", required=True, help="MinIO access key")
    parser.add_argument("--minio-secret-key", required=True, help="MinIO secret key")
    parser.add_argument("--minio-bucket", required=True, help="MinIO bucket containing parquet data")
    parser.add_argument("--minio-prefix", required=True, help="MinIO prefix containing parquet data")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    out_path = Path(args.output)
    if not data_dir.exists():
        raise FileNotFoundError(f"Data dir not found: {data_dir}")

    parquet_df = list_and_download_parquet_files(
        endpoint=args.minio_endpoint,
        access_key=args.minio_access_key,
        secret_key=args.minio_secret_key,
        bucket=args.minio_bucket,
        prefix=args.minio_prefix,
    )
    latest_ticks = latest_ticks_from_parquet(parquet_df)

    tickers: list[str] = []
    data_dict: dict[str, pd.DataFrame] = {}
    last_event_dates: list[pd.Timestamp] = []

    for ticker, price, event_time in latest_ticks:
        csv_path = data_dir / f"{ticker}.csv"
        if not csv_path.exists():
            print(f"[skip] missing raw CSV for {ticker}: {csv_path}")
            continue

        raw_df = load_raw_price_csv(csv_path, ticker)
        merged_df = merge_kafka_tick_into_history(raw_df, price, event_time)
        feat_df = engineer_features(merged_df)

        if len(feat_df) <= args.lookback:
            print(f"[skip] not enough engineered rows for {ticker}: {len(feat_df)}")
            continue

        tickers.append(ticker)
        data_dict[ticker] = feat_df
        last_event_dates.append(pd.Timestamp(event_time).tz_localize(None).normalize())

    if not tickers:
        raise ValueError("No usable tickers available after merging MinIO parquet data with local history.")

    common_index = None
    for ticker in tickers:
        idx = data_dict[ticker].index
        common_index = idx if common_index is None else common_index.intersection(idx)

    common_index = common_index.sort_values()
    if common_index is None or len(common_index) <= args.lookback:
        raise ValueError(
            f"Not enough common dates after aligning MinIO-updated histories. Need > {args.lookback}, got {0 if common_index is None else len(common_index)}"
        )

    for ticker in tickers:
        data_dict[ticker] = data_dict[ticker].loc[common_index].copy()

    full_node_3d = np.stack(
        [data_dict[t][FEATURE_COLS].values.astype(np.float32) for t in tickers],
        axis=1,
    )
    close_only_3d = np.stack(
        [data_dict[t][["Close"]].values.astype(np.float32) for t in tickers],
        axis=1,
    )
    return_2d = np.stack(
        [data_dict[t]["Return"].values.astype(np.float32) for t in tickers],
        axis=1,
    )

    t_last = len(common_index) - 1
    seq = close_only_3d[t_last - args.lookback + 1:t_last + 1, :, :]
    seq = np.transpose(seq, (1, 0, 2))

    node_x = full_node_3d[t_last, :, :]
    last_close = full_node_3d[t_last, :, TARGET_IDX]

    train_start_t = max(0, t_last - (252 * 2) + 1)
    train_end_t = t_last
    adj_norm, adj_raw = build_combined_graph_from_train_window(
        return_2d=return_2d,
        train_start_t=train_start_t,
        train_end_t=train_end_t,
    )

    x_seq = np.expand_dims(seq.astype(np.float32), axis=0)
    x_node = np.expand_dims(node_x.astype(np.float32), axis=0)
    adj = np.expand_dims(adj_norm.astype(np.float32), axis=0)
    last_close = np.expand_dims(last_close.astype(np.float32), axis=0)

    effective_as_of_date = max(last_event_dates).date().isoformat() if last_event_dates else str(common_index[t_last].date())

    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        out_path,
        X_seq=x_seq,
        X_node=x_node,
        A=adj,
        last_close=last_close,
        tickers=np.array(tickers, dtype=object),
        as_of_date=np.array(effective_as_of_date, dtype=object),
        adj_raw=adj_raw.astype(np.float32),
        feature_cols=np.array(FEATURE_COLS, dtype=object),
        minio_bucket=np.array(args.minio_bucket, dtype=object),
        minio_prefix=np.array(args.minio_prefix, dtype=object),
    )

    print("=" * 80)
    print(f"Saved MinIO-driven inference bundle to: {out_path}")
    print(f"tickers_used: {tickers}")
    print(f"as_of_date: {effective_as_of_date}")
    print(f"X_seq shape: {x_seq.shape}")
    print(f"X_node shape: {x_node.shape}")
    print(f"A shape: {adj.shape}")
    print("=" * 80)


if __name__ == "__main__":
    main()
