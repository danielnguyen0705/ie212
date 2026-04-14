# src/features.py

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


def build_feature_tensor(
    data_dict: Dict[str, pd.DataFrame],
    tickers: List[str],
    feature_cols: List[str]
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, pd.DatetimeIndex]:
    dates = data_dict[tickers[0]].index

    T = len(dates)
    N = len(tickers)
    F = len(feature_cols)

    features_3d = np.zeros((T, N, F), dtype=np.float32)
    close_2d = np.zeros((T, N), dtype=np.float32)
    return_2d = np.zeros((T, N), dtype=np.float32)

    for j, ticker in enumerate(tickers):
        df = data_dict[ticker]

        features_3d[:, j, :] = df[feature_cols].values.astype(np.float32)
        close_2d[:, j] = df["Close"].values.astype(np.float32)
        return_2d[:, j] = df["Return"].values.astype(np.float32)

    return features_3d, close_2d, return_2d, dates