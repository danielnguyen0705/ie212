# scripts/run_train.py

import os

from src.config import TICKERS, START_DATE, END_DATE, FEATURE_COLS
from src.data_loader import load_all_tickers, align_common_index
from src.features import build_feature_tensor


def main():
    print("=== LOAD DATA TEST ===")

    data_dict = load_all_tickers(TICKERS, START_DATE, END_DATE)
    data_dict, common_index = align_common_index(data_dict, TICKERS)

    print("Số ngày chung:", len(common_index))
    print("Ngày đầu:", common_index.min())
    print("Ngày cuối:", common_index.max())

    os.makedirs("data/raw", exist_ok=True)

    for ticker in TICKERS:
        save_path = f"data/raw/{ticker}.csv"
        data_dict[ticker].to_csv(save_path)
        print(f"Saved: {save_path} | shape={data_dict[ticker].shape}")

    features_3d, close_2d, return_2d, dates = build_feature_tensor(
        data_dict=data_dict,
        tickers=TICKERS,
        feature_cols=FEATURE_COLS
    )

    print("\n=== FEATURE TENSOR SHAPES ===")
    print("features_3d:", features_3d.shape)
    print("close_2d:", close_2d.shape)
    print("return_2d:", return_2d.shape)
    print("dates:", len(dates))


if __name__ == "__main__":
    main()