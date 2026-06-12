import os
import random
import threading
import time
from datetime import datetime, timezone
from typing import Any, Optional

import psycopg2


DEMO_RUNTIME_MODE = os.getenv("DEMO_RUNTIME_MODE", "true").lower() in ("true", "1", "yes")

MAX_HISTORY = 200
DRIFT_GUARD_PCT = 0.02


def _get_db_config() -> dict[str, Any]:
    return {
        "host": os.getenv("IE212_API_POSTGRES_HOST", "postgres"),
        "port": int(os.getenv("IE212_API_POSTGRES_PORT", "5432")),
        "dbname": os.getenv("IE212_API_POSTGRES_DB", "stock_project"),
        "user": os.getenv("IE212_API_POSTGRES_USER", "stock_user"),
        "password": os.getenv("IE212_API_POSTGRES_PASSWORD", "change_me_postgres"),
    }


def _query_latest_predictions() -> list[dict]:
    try:
        conn = psycopg2.connect(**_get_db_config())
        cur = conn.cursor()
        cur.execute("""
            WITH latest AS (
                SELECT prediction_run_id
                FROM stock.inference_predictions
                GROUP BY prediction_run_id
                ORDER BY MAX(created_at) DESC
                LIMIT 1
            )
            SELECT
                p.ticker,
                p.last_close,
                p.pred_close,
                p.pred_return,
                p.graph_gate,
                p.prediction_run_id
            FROM stock.inference_predictions p
            JOIN latest l ON p.prediction_run_id = l.prediction_run_id
            ORDER BY p.ticker
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [
            {
                "ticker": r[0],
                "last_close": float(r[1]),
                "pred_close": float(r[2]),
                "pred_return": float(r[3]) if r[3] is not None else 0.0,
                "graph_gate": float(r[4]) if r[4] is not None else None,
                "run_id": r[5],
            }
            for r in rows
        ]
    except Exception:
        return []


def _compute_signal(pred_return: float, graph_gate: Optional[float]) -> str:
    if graph_gate is not None and graph_gate < 0.3:
        return "STAND_OUT"
    if pred_return > 0.001:
        return "BUY"
    if pred_return < -0.001:
        return "SELL_OR_AVOID"
    return "HOLD"


class DemoStreamEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self._ticker_data: dict[str, dict] = {}
        self._histories: dict[str, list[dict]] = {}
        self._predictions: dict[str, dict] = {}
        self._loaded = False
        self._thread = None
        self._stop_event = threading.Event()

    def _ensure_loaded(self):
        if self._loaded:
            return
        preds = _query_latest_predictions()
        with self._lock:
            for p in preds:
                ticker = p["ticker"]
                self._predictions[ticker] = p
                self._ticker_data[ticker] = {
                    "current_price": p["last_close"],
                    "last_close": p["last_close"],
                    "pred_close": p["pred_close"],
                    "pred_return": p["pred_return"],
                    "graph_gate": p["graph_gate"],
                    "run_id": p["run_id"],
                }
                self._histories[ticker] = []
            self._loaded = True

            # Tạo điểm dữ liệu ban đầu
            for t in self._ticker_data.keys():
                self._generate_point_locked(t)

            # Khởi động luồng chạy ngầm sinh dữ liệu mỗi 3 giây
            if self._thread is None:
                self._stop_event.clear()
                self._thread = threading.Thread(target=self._run_loop, daemon=True)
                self._thread.start()

    def _run_loop(self):
        while not self._stop_event.is_set():
            time.sleep(3.0)
            with self._lock:
                for t in self._ticker_data.keys():
                    self._generate_point_locked(t)

    def reload(self):
        with self._lock:
            self._loaded = False
            self._ticker_data.clear()
            self._histories.clear()
            self._predictions.clear()
        self._ensure_loaded()

    def get_tickers(self) -> list[str]:
        self._ensure_loaded()
        with self._lock:
            return sorted(self._ticker_data.keys())

    def _generate_point_locked(self, ticker: str) -> Optional[dict]:
        td = self._ticker_data.get(ticker)
        if td is None:
            return None

        prev_price = td["current_price"]
        last_close = td["last_close"]
        pred_return = td["pred_return"]

        noise = random.uniform(-0.0008, 0.0008)
        bias = pred_return * 0.05 if pred_return else 0.0
        new_price = prev_price * (1.0 + noise + bias)

        upper = last_close * (1.0 + DRIFT_GUARD_PCT)
        lower = last_close * (1.0 - DRIFT_GUARD_PCT)
        if new_price > upper:
            new_price = upper - abs(noise) * last_close
        elif new_price < lower:
            new_price = lower + abs(noise) * last_close

        td["current_price"] = new_price

        delta = new_price - last_close
        signal = _compute_signal(pred_return, td["graph_gate"])

        point = {
            "ticker": ticker,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "runtime_price": round(new_price, 4),
            "last_close": last_close,
            "pred_close": td["pred_close"],
            "pred_return": pred_return,
            "delta": round(delta, 6),
            "signal": signal,
            "graph_gate": td["graph_gate"],
            "source": "DEMO_RUNTIME_MODE",
        }

        hist = self._histories.setdefault(ticker, [])
        hist.append(point)
        if len(hist) > MAX_HISTORY:
            hist[:] = hist[-MAX_HISTORY:]

        return point

    def get_history(self, ticker: str, limit: int = 100) -> list[dict]:
        self._ensure_loaded()
        with self._lock:
            hist = self._histories.get(ticker, [])
            return hist[-limit:]

    def get_latest(self, ticker: str) -> Optional[dict]:
        self._ensure_loaded()
        with self._lock:
            hist = self._histories.get(ticker, [])
            return hist[-1] if hist else None

    def get_all_latest(self) -> list[dict]:
        self._ensure_loaded()
        with self._lock:
            points = []
            for t in sorted(self._ticker_data.keys()):
                hist = self._histories.get(t, [])
                if hist:
                    points.append(hist[-1])
            return points


demo_engine = DemoStreamEngine()
