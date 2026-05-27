# scripts/run_train.py

import argparse
import os

import _path_setup

from src.config import TICKERS, START_DATE, END_DATE, FEATURE_COLS
from src.data_loader import load_all_tickers, align_common_index
from src.features import build_feature_tensor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        default="data/raw",
        help="Directory to read/write cached ticker CSV files",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Ignore local cached CSV files and force download again",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Number of retries for each yfinance strategy",
    )
    args = parser.parse_args()

    print("=== LOAD DATA TEST ===")

    data_dict = load_all_tickers(
        TICKERS,
        START_DATE,
        END_DATE,
        data_dir=args.data_dir,
        prefer_local=not args.refresh,
        save_downloaded=True,
        max_retries=args.max_retries,
    )
    data_dict, common_index = align_common_index(data_dict, TICKERS)

    print("So ngay chung:", len(common_index))
    print("Ngay dau:", common_index.min())
    print("Ngay cuoi:", common_index.max())

    os.makedirs(args.data_dir, exist_ok=True)

    for ticker in TICKERS:
        save_path = os.path.join(args.data_dir, f"{ticker}.csv")
        data_dict[ticker].to_csv(save_path)
        print(f"Saved: {save_path} | shape={data_dict[ticker].shape}")

    features_3d, close_2d, return_2d, dates = build_feature_tensor(
        data_dict=data_dict,
        tickers=TICKERS,
        feature_cols=FEATURE_COLS,
    )

    print("\n=== FEATURE TENSOR SHAPES ===")
    print("features_3d:", features_3d.shape)
    print("close_2d:", close_2d.shape)
    print("return_2d:", return_2d.shape)
    print("dates:", len(dates))


if __name__ == "__main__":
    main()
