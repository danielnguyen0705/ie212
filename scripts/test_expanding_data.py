# scripts/test_expanding_data.py

import _path_setup

from src.config import (
    TICKERS, START_DATE, END_DATE, FEATURE_COLS,
    TARGET_IDX, LOOKBACK, EXP_TEST_DAYS, EXP_INITIAL_TRAIN_DAYS
)
from src.data_loader import load_all_tickers, align_common_index
from src.features import build_feature_tensor
from src.expanding import (
    fit_and_scale_for_expanding_initial_window,
    build_samples_for_target_range,
)
from src.graph_builder import normalize_adjacency


def main():
    print("=== TEST EXPANDING DATA ===")

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

    print("Scaled shape:", scaled_features_3d.shape)
    print("Train start t:", train_start_t, "| Date:", dates[train_start_t])
    print("Train end t:", train_end_t, "| Date:", dates[train_end_t])

    N = len(TICKERS)
    adj_identity = normalize_adjacency(__import__("numpy").eye(N, dtype=float))

    sample_pack = build_samples_for_target_range(
        close_only_3d=close_only_3d,
        full_node_3d=full_node_3d,
        adj_norm=adj_identity,
        start_t=max(train_start_t + LOOKBACK, LOOKBACK),
        end_t=train_end_t,
        lookback=LOOKBACK,
        dates=dates,
        target_idx=TARGET_IDX
    )

    print("\n=== SAMPLE PACK SHAPES ===")
    print("X_seq:", sample_pack["X_seq"].shape)
    print("X_node:", sample_pack["X_node"].shape)
    print("A:", sample_pack["A"].shape)
    print("y_res:", sample_pack["y_res"].shape)
    print("y_close:", sample_pack["y_close"].shape)
    print("last_close:", sample_pack["last_close"].shape)
    print("dates:", sample_pack["dates"].shape)


if __name__ == "__main__":
    main()
