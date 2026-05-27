# scripts/test_graph_builder.py

import numpy as np
import _path_setup

from src.config import (
    TICKERS,
    START_DATE,
    END_DATE,
    FEATURE_COLS,
    EXP_TEST_DAYS,
    EXP_INITIAL_TRAIN_DAYS,
)
from src.data_loader import load_all_tickers, align_common_index
from src.features import build_feature_tensor
from src.graph_builder import build_combined_graph_from_train_window


def main():
    print("=== TEST GRAPH BUILDER ===")

    data_dict = load_all_tickers(TICKERS, START_DATE, END_DATE)
    data_dict, common_index = align_common_index(data_dict, TICKERS)

    features_3d, close_2d, return_2d, dates = build_feature_tensor(
        data_dict=data_dict,
        tickers=TICKERS,
        feature_cols=FEATURE_COLS
    )

    first_test_t = len(dates) - EXP_TEST_DAYS
    train_start_t = max(0, first_test_t - EXP_INITIAL_TRAIN_DAYS)
    train_end_t = first_test_t - 1

    adj_norm, adj_raw, corr_raw, debug_info = build_combined_graph_from_train_window(
        return_2d=return_2d,
        tickers=TICKERS,
        train_start_t=train_start_t,
        train_end_t=train_end_t
    )

    print("Train start t:", train_start_t, "| Date:", dates[train_start_t])
    print("Train end t:", train_end_t, "| Date:", dates[train_end_t])

    print("\n=== GRAPH SHAPES ===")
    print("adj_norm:", adj_norm.shape)
    print("adj_raw:", adj_raw.shape)
    print("corr_raw:", corr_raw.shape)

    print("\n=== GRAPH DEBUG ===")
    print(debug_info)

    print("\n=== ADJ RAW (first 5x5) ===")
    print(np.round(adj_raw[:5, :5], 3))

    print("\n=== ADJ NORM (first 5x5) ===")
    print(np.round(adj_norm[:5, :5], 3))


if __name__ == "__main__":
    main()
