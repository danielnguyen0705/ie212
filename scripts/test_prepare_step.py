# scripts/test_prepare_step.py

import _path_setup

from src.config import (
    TICKERS,
    START_DATE,
    END_DATE,
    FEATURE_COLS,
    TARGET_IDX,
    LOOKBACK,
    EXP_TEST_DAYS,
    EXP_VAL_DAYS,
    EXP_INITIAL_TRAIN_DAYS,
)
from src.data_loader import load_all_tickers, align_common_index
from src.features import build_feature_tensor
from src.expanding import (
    fit_and_scale_for_expanding_initial_window,
    prepare_expanding_step_data,
)


def main():
    print("=== TEST PREPARE EXPANDING STEP ===")

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

    test_t = first_test_t

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

    print("Test date:", meta["test_date"])
    print("Graph debug:", meta["graph_debug"])

    print("\n=== TRAIN PACK ===")
    print("X_seq:", train_pack["X_seq"].shape)
    print("X_node:", train_pack["X_node"].shape)
    print("A:", train_pack["A"].shape)
    print("y_close:", train_pack["y_close"].shape)

    print("\n=== VAL PACK ===")
    print("X_seq:", val_pack["X_seq"].shape)
    print("X_node:", val_pack["X_node"].shape)
    print("A:", val_pack["A"].shape)
    print("y_close:", val_pack["y_close"].shape)

    print("\n=== TEST PACK ===")
    print("X_seq:", test_pack["X_seq"].shape)
    print("X_node:", test_pack["X_node"].shape)
    print("A:", test_pack["A"].shape)
    print("y_close:", test_pack["y_close"].shape)


if __name__ == "__main__":
    main()
