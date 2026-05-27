import argparse
import csv
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import _path_setup

from src.config import TICKERS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish stock price ticks to Kafka for the IE212 streaming pipeline."
    )
    parser.add_argument(
        "--bootstrap-servers",
        default=os.getenv("IE212_KAFKA_BOOTSTRAP_SERVERS", "localhost:29092"),
        help="Kafka bootstrap servers. Use kafka:9092 inside Docker, localhost:29092 on host.",
    )
    parser.add_argument(
        "--topic",
        default=os.getenv("IE212_KAFKA_TOPIC", "stock-price"),
        help="Kafka topic to publish stock price events into.",
    )
    parser.add_argument(
        "--tickers",
        nargs="*",
        default=None,
        help="Optional ticker override. Defaults to IE212_PRODUCER_TICKERS or src.config.TICKERS.",
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=float(os.getenv("IE212_PRODUCER_INTERVAL_SECONDS", "30")),
        help="Sleep interval between publish rounds.",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=int(os.getenv("IE212_PRODUCER_MAX_ITERATIONS", "0")),
        help="Number of publish rounds. Use 0 for infinite loop.",
    )
    parser.add_argument(
        "--source",
        choices=("auto", "yfinance", "csv"),
        default=os.getenv("IE212_PRODUCER_SOURCE", "auto"),
        help="Data source strategy. auto tries yfinance first, then local CSV fallback.",
    )
    parser.add_argument(
        "--csv-dir",
        default=os.getenv("IE212_PRODUCER_CSV_DIR", "data/raw"),
        help="Directory containing local CSV files for fallback or offline replay.",
    )
    parser.add_argument(
        "--client-id",
        default=os.getenv("IE212_PRODUCER_CLIENT_ID", "ie212-stock-producer"),
        help="Kafka client id.",
    )
    parser.add_argument(
        "--connect-retries",
        type=int,
        default=int(os.getenv("IE212_PRODUCER_CONNECT_RETRIES", "10")),
        help="Kafka connection retries before giving up.",
    )
    parser.add_argument(
        "--retry-delay-seconds",
        type=float,
        default=float(os.getenv("IE212_PRODUCER_RETRY_DELAY_SECONDS", "5")),
        help="Delay between Kafka connection retries.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the messages that would be sent without connecting to Kafka.",
    )
    return parser.parse_args()


def resolve_tickers(cli_tickers: list[str] | None) -> list[str]:
    if cli_tickers:
        return [ticker.upper() for ticker in cli_tickers]

    env_tickers = os.getenv("IE212_PRODUCER_TICKERS", "").strip()
    if env_tickers:
        return [part.strip().upper() for part in env_tickers.split(",") if part.strip()]

    return list(TICKERS)


def get_price_from_yfinance(ticker: str) -> tuple[float, str]:
    import yfinance as yf

    ticker_obj = yf.Ticker(ticker)

    fast_info = getattr(ticker_obj, "fast_info", None) or {}
    for key in ("lastPrice", "last_price", "regularMarketPrice"):
        price = fast_info.get(key)
        if price is not None:
            return float(price), "yfinance.fast_info"

    history = ticker_obj.history(period="5d", interval="1d", auto_adjust=False)
    if history.empty:
        raise ValueError(f"No yfinance history rows returned for {ticker}")

    close_value = history["Close"].dropna().iloc[-1]
    return float(close_value), "yfinance.history"


def get_price_from_csv(csv_dir: Path, ticker: str) -> tuple[float, str]:
    csv_path = csv_dir / f"{ticker}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found for ticker {ticker}: {csv_path}")

    last_row = None
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            last_row = row

    if last_row is None:
        raise ValueError(f"CSV file has no rows: {csv_path}")

    close_raw = last_row.get("Close") or last_row.get("close")
    if close_raw is None:
        raise KeyError(f"CSV missing Close column: {csv_path}")

    return float(close_raw), f"csv:{csv_path.name}"


def resolve_price(ticker: str, source: str, csv_dir: Path) -> tuple[float, str]:
    if source == "yfinance":
        return get_price_from_yfinance(ticker)
    if source == "csv":
        return get_price_from_csv(csv_dir, ticker)

    errors: list[str] = []
    for strategy in (get_price_from_yfinance, lambda symbol: get_price_from_csv(csv_dir, symbol)):
        try:
            return strategy(ticker)
        except Exception as exc:  # pragma: no cover - best effort fallback path
            errors.append(str(exc))
    raise RuntimeError(f"Could not resolve price for {ticker}. Errors: {' | '.join(errors)}")


def build_message(ticker: str, price: float, price_source: str) -> dict[str, object]:
    return {
        "symbol": ticker,
        "price": round(price, 4),
        "event_time": datetime.now(timezone.utc).isoformat(),
        "source": price_source,
    }


def create_producer(args: argparse.Namespace) -> Any:
    from kafka import KafkaProducer
    from kafka.errors import NoBrokersAvailable

    last_error: Exception | None = None
    for attempt in range(1, args.connect_retries + 1):
        try:
            producer = KafkaProducer(
                bootstrap_servers=args.bootstrap_servers,
                client_id=args.client_id,
                acks="all",
                retries=5,
                value_serializer=lambda value: json.dumps(value).encode("utf-8"),
                key_serializer=lambda key: key.encode("utf-8"),
                request_timeout_ms=15000,
            )
            if producer.bootstrap_connected():
                print(f"[producer] Connected to Kafka on attempt {attempt}: {args.bootstrap_servers}")
                return producer
            producer.close()
            raise NoBrokersAvailable(f"bootstrap not connected: {args.bootstrap_servers}")
        except Exception as exc:  # pragma: no cover - depends on runtime infra
            last_error = exc
            print(f"[producer] Kafka connection attempt {attempt}/{args.connect_retries} failed: {exc}")
            if attempt < args.connect_retries:
                time.sleep(args.retry_delay_seconds)

    raise RuntimeError(f"Could not connect to Kafka after {args.connect_retries} attempts") from last_error


def publish_round(
    *,
    producer: Any,
    topic: str,
    tickers: list[str],
    source: str,
    csv_dir: Path,
    dry_run: bool,
) -> int:
    published = 0
    for ticker in tickers:
        try:
            price, price_source = resolve_price(ticker, source=source, csv_dir=csv_dir)
            if math.isnan(price):
                raise ValueError(f"Resolved NaN price for {ticker}")
            message = build_message(ticker, price, price_source)

            if dry_run:
                print(f"[dry-run] topic={topic} key={ticker} value={json.dumps(message)}")
            else:
                assert producer is not None
                future = producer.send(topic, key=ticker, value=message)
                metadata = future.get(timeout=20)
                print(
                    f"[producer] sent {ticker} price={message['price']} "
                    f"topic={metadata.topic} partition={metadata.partition} offset={metadata.offset}"
                )
            published += 1
        except Exception as exc:
            print(f"[producer] skip {ticker}: {exc}")

    if producer is not None and published > 0:
        producer.flush()

    return published


def main() -> None:
    args = parse_args()
    tickers = resolve_tickers(args.tickers)
    csv_dir = Path(args.csv_dir)

    print(
        "[producer] config",
        json.dumps(
            {
                "bootstrap_servers": args.bootstrap_servers,
                "topic": args.topic,
                "tickers": tickers,
                "interval_seconds": args.interval_seconds,
                "max_iterations": args.max_iterations,
                "source": args.source,
                "csv_dir": str(csv_dir),
                "dry_run": args.dry_run,
            }
        ),
    )

    producer = None if args.dry_run else create_producer(args)

    iteration = 0
    try:
        while True:
            iteration += 1
            print(f"[producer] publish round {iteration} started")
            published = publish_round(
                producer=producer,
                topic=args.topic,
                tickers=tickers,
                source=args.source,
                csv_dir=csv_dir,
                dry_run=args.dry_run,
            )
            print(f"[producer] publish round {iteration} finished with {published} message(s)")

            if args.max_iterations > 0 and iteration >= args.max_iterations:
                break

            time.sleep(args.interval_seconds)
    except KeyboardInterrupt:
        print("[producer] interrupted by user")
    finally:
        if producer is not None:
            producer.flush()
            producer.close()


if __name__ == "__main__":
    main()
