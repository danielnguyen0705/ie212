# src/data_loader.py

from pathlib import Path
from time import sleep
from typing import Dict, List, Tuple

import pandas as pd
import yfinance as yf


PRICE_COLS = ["Open", "High", "Low", "Close", "Volume"]


def _postprocess_price_frame(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if df.empty:
        raise ValueError(f"No rows returned for {ticker}")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")
    elif "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
    else:
        df.index = pd.to_datetime(df.index)

    keep_cols = [c for c in PRICE_COLS if c in df.columns]
    df = df[keep_cols].copy()

    if "Close" not in df.columns:
        raise ValueError(f"Missing Close column for {ticker}")
    if "Volume" not in df.columns:
        df["Volume"] = 0.0

    df["Close"] = pd.to_numeric(df["Close"], errors="coerce").ffill()
    df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce").fillna(0.0)

    for col in ["Open", "High", "Low"]:
        if col not in df.columns:
            df[col] = df["Close"]
        df[col] = pd.to_numeric(df[col], errors="coerce").ffill()

    df = df.dropna(subset=["Close"]).copy()
    df = df.sort_index()

    df["Return"] = df["Close"].pct_change().fillna(0.0)
    df["MA5"] = df["Close"].rolling(5).mean()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["Volatility5"] = df["Return"].rolling(5).std()
    df["Volatility20"] = df["Return"].rolling(20).std()

    df = df.dropna().copy()
    df.index = pd.to_datetime(df.index)

    if df.empty:
        raise ValueError(f"Not enough usable rows after feature engineering for {ticker}")

    return df


def load_one_ticker_from_csv(csv_path: Path, ticker: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    return _postprocess_price_frame(df, ticker)


def _download_with_yfinance_download(ticker: str, start: str, end: str) -> pd.DataFrame:
    return yf.download(
        ticker,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False,
    )


def _download_with_yfinance_history(ticker: str, start: str, end: str) -> pd.DataFrame:
    return yf.Ticker(ticker).history(
        start=start,
        end=end,
        interval="1d",
        auto_adjust=False,
    )


def download_one_ticker(
    ticker: str,
    start: str,
    end: str,
    max_retries: int = 3,
    retry_sleep_seconds: float = 2.0,
) -> pd.DataFrame:
    attempts: list[str] = []

    for attempt in range(1, max_retries + 1):
        try:
            df = _download_with_yfinance_download(ticker, start, end)
            return _postprocess_price_frame(df, ticker)
        except Exception as exc:
            attempts.append(f"download attempt {attempt}: {exc}")
            if attempt < max_retries:
                sleep(retry_sleep_seconds)

    for attempt in range(1, max_retries + 1):
        try:
            df = _download_with_yfinance_history(ticker, start, end)
            return _postprocess_price_frame(df, ticker)
        except Exception as exc:
            attempts.append(f"history attempt {attempt}: {exc}")
            if attempt < max_retries:
                sleep(retry_sleep_seconds)

    details = " | ".join(attempts)
    raise ValueError(f"Khong tai duoc du lieu cho {ticker}. Details: {details}")


def load_all_tickers(
    tickers: List[str],
    start: str,
    end: str,
    data_dir: str | Path = "data/raw",
    prefer_local: bool = True,
    save_downloaded: bool = True,
    max_retries: int = 3,
) -> Dict[str, pd.DataFrame]:
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    data_dict: Dict[str, pd.DataFrame] = {}
    errors: Dict[str, str] = {}

    for ticker in tickers:
        csv_path = data_dir / f"{ticker}.csv"

        if prefer_local and csv_path.exists():
            try:
                data_dict[ticker] = load_one_ticker_from_csv(csv_path, ticker)
                print(f"[cache] {ticker}: loaded from {csv_path}")
                continue
            except Exception as exc:
                print(f"[cache-miss] {ticker}: local file unusable ({exc}), retrying download")

        try:
            df = download_one_ticker(
                ticker=ticker,
                start=start,
                end=end,
                max_retries=max_retries,
            )
            data_dict[ticker] = df

            if save_downloaded:
                df.to_csv(csv_path)
                print(f"[download] {ticker}: saved to {csv_path}")
        except Exception as exc:
            errors[ticker] = str(exc)

    if errors:
        error_lines = [f"{ticker}: {message}" for ticker, message in errors.items()]
        raise ValueError("Khong tai duoc du lieu cho mot so ticker:\n" + "\n".join(error_lines))

    return data_dict


def align_common_index(
    data_dict: Dict[str, pd.DataFrame],
    tickers: List[str],
) -> Tuple[Dict[str, pd.DataFrame], pd.DatetimeIndex]:
    common_index = None

    for ticker in tickers:
        idx = data_dict[ticker].index
        common_index = idx if common_index is None else common_index.intersection(idx)

    common_index = common_index.sort_values()

    if len(common_index) == 0:
        raise ValueError("Khong tim duoc tap ngay giao nhau giua cac ticker")

    aligned_dict = {}
    for ticker in tickers:
        aligned_dict[ticker] = data_dict[ticker].loc[common_index].copy()

    return aligned_dict, common_index
