# src/data_loader.py

from typing import Dict, List, Tuple

import pandas as pd
import yfinance as yf


def download_one_ticker(ticker: str, start: str, end: str) -> pd.DataFrame:
    df = yf.download(
        ticker,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False
    )

    if df.empty:
        raise ValueError(f"Không tải được dữ liệu cho {ticker}")

    # nếu yfinance trả multi-index columns
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    keep_cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    df = df[keep_cols].copy()

    df["Close"] = df["Close"].ffill()
    df["Volume"] = df["Volume"].fillna(0.0)

    # feature engineering
    df["Return"] = df["Close"].pct_change().fillna(0.0)
    df["MA5"] = df["Close"].rolling(5).mean()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["Volatility5"] = df["Return"].rolling(5).std()
    df["Volatility20"] = df["Return"].rolling(20).std()

    df = df.dropna().copy()
    df.index = pd.to_datetime(df.index)
    return df


def load_all_tickers(tickers: List[str], start: str, end: str) -> Dict[str, pd.DataFrame]:
    data_dict = {}
    for ticker in tickers:
        data_dict[ticker] = download_one_ticker(ticker, start, end)
    return data_dict


def align_common_index(data_dict: Dict[str, pd.DataFrame], tickers: List[str]) -> Tuple[Dict[str, pd.DataFrame], pd.DatetimeIndex]:
    common_index = None

    for ticker in tickers:
        idx = data_dict[ticker].index
        common_index = idx if common_index is None else common_index.intersection(idx)

    common_index = common_index.sort_values()

    aligned_dict = {}
    for ticker in tickers:
        aligned_dict[ticker] = data_dict[ticker].loc[common_index].copy()

    return aligned_dict, common_index