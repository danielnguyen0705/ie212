from pathlib import Path
import os
from contextlib import contextmanager
from typing import Any, List, Optional

import psycopg2
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import csv


APP_TITLE = "IE212 Prediction API"
APP_VERSION = "1.1.0"

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

class PredictionItem(BaseModel):
    ticker: str
    last_close: float
    pred_close: float
    pred_return: Optional[float] = None
    graph_gate: Optional[float] = None
    created_at: Optional[str] = None


class RunSummary(BaseModel):
    run_id: str
    as_of_date: Optional[str] = None
    model_name: str
    row_count: int
    first_created_at: Optional[str] = None
    last_created_at: Optional[str] = None


class RecentRunsResponse(BaseModel):
    count: int
    items: List[RunSummary]


class RunDetailResponse(BaseModel):
    run_id: str
    as_of_date: Optional[str] = None
    model_name: str
    row_count: int
    items: List[PredictionItem]


class DashboardSummaryResponse(BaseModel):
    latest_run_id: str
    model_name: str
    as_of_date: Optional[str] = None
    row_count: int
    ticker_count: int
    avg_pred_return: Optional[float] = None
    max_pred_return: Optional[float] = None
    min_pred_return: Optional[float] = None
    last_updated: Optional[str] = None


class TickersResponse(BaseModel):
    tickers: List[str]


class PredictionHistoryItem(BaseModel):
    run_id: str
    as_of_date: Optional[str] = None
    last_close: float
    pred_close: float
    pred_return: Optional[float] = None
    graph_gate: Optional[float] = None
    model_name: Optional[str] = None
    created_at: Optional[str] = None


class PredictionHistoryResponse(BaseModel):
    ticker: str
    items: List[PredictionHistoryItem]


class PriceHistoryItem(BaseModel):
    date: str
    close: float


class PriceHistoryResponse(BaseModel):
    ticker: str
    days: int
    items: List[PriceHistoryItem]

def normalize_prediction_row(row) -> dict[str, Any]:
    return {
        "ticker": row[3],
        "last_close": float(row[4]),
        "pred_close": float(row[5]),
        "pred_return": None if row[6] is None else float(row[6]),
        "graph_gate": None if row[7] is None else float(row[7]),
        "created_at": None if row[8] is None else row[8].isoformat(),
    }


def latest_run_id(cur) -> str:
    cur.execute(
        """
        SELECT prediction_run_id
        FROM stock.inference_predictions
        GROUP BY prediction_run_id
        ORDER BY MAX(created_at) DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="No prediction runs found.")
    return row[0]

def find_raw_csv_for_ticker(ticker: str) -> Path:
    data_raw_dir = BASE_DIR.parent.parent / "data" / "raw"
    candidates = [
        data_raw_dir / f"{ticker}.csv",
        data_raw_dir / f"{ticker.lower()}.csv",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise HTTPException(status_code=404, detail=f"Raw CSV not found for ticker: {ticker}")


def env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def get_db_config() -> dict[str, Any]:
    return {
        "host": env("IE212_API_POSTGRES_HOST", "postgres"),
        "port": int(env("IE212_API_POSTGRES_PORT", "5432")),
        "dbname": env("IE212_API_POSTGRES_DB", "stock_project"),
        "user": env("IE212_API_POSTGRES_USER", "stock_user"),
        "password": env("IE212_API_POSTGRES_PASSWORD", "change_me_postgres"),
    }


@contextmanager
def get_conn():
    conn = psycopg2.connect(**get_db_config())
    try:
        yield conn
    finally:
        conn.close()


app = FastAPI(title=APP_TITLE, version=APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "service": APP_TITLE,
        "version": APP_VERSION,
        "message": "IE212 FastAPI service is running.",
        "endpoints": [
            "/health",
            "/dashboard",
            "/predictions/runs/latest",
            "/predictions/runs/recent",
            "/predictions/latest",
            "/predictions/runs/{run_id}",
        ],
    }


@app.get("/dashboard")
def dashboard():
    dashboard_file = STATIC_DIR / "index.html"
    if not dashboard_file.exists():
        raise HTTPException(status_code=404, detail="Dashboard file not found.")
    return FileResponse(dashboard_file)


@app.get("/health")
def health():
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                db_ok = cur.fetchone()[0] == 1

                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = 'stock'
                      AND table_name = 'inference_predictions'
                    """
                )
                table_exists = cur.fetchone()[0] == 1

        return {
            "status": "ok" if db_ok and table_exists else "degraded",
            "database": db_ok,
            "inference_predictions_table": table_exists,
        }
    except Exception as e:
        return {
            "status": "error",
            "database": False,
            "detail": str(e),
        }


@app.get("/predictions/runs/latest", response_model=RunDetailResponse)
def get_latest_run():
    with get_conn() as conn:
        with conn.cursor() as cur:
            run_id = latest_run_id(cur)

            cur.execute(
                """
                SELECT
                    prediction_run_id,
                    as_of_date,
                    model_name,
                    ticker,
                    last_close,
                    pred_close,
                    pred_return,
                    graph_gate,
                    created_at
                FROM stock.inference_predictions
                WHERE prediction_run_id = %s
                ORDER BY ticker ASC
                """,
                (run_id,),
            )
            rows = cur.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="No prediction rows found for latest run.")

    first = rows[0]
    return {
        "run_id": run_id,
        "as_of_date": None if first[1] is None else str(first[1]),
        "model_name": first[2],
        "row_count": len(rows),
        "items": [normalize_prediction_row(r) for r in rows],
    }


@app.get("/predictions/runs/recent", response_model=RecentRunsResponse)
def get_recent_runs(limit: int = Query(default=10, ge=1, le=100)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    prediction_run_id,
                    as_of_date,
                    model_name,
                    COUNT(*) AS row_count,
                    MIN(created_at) AS first_created_at,
                    MAX(created_at) AS last_created_at
                FROM stock.inference_predictions
                GROUP BY prediction_run_id, as_of_date, model_name
                ORDER BY MAX(created_at) DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()

    return {
        "count": len(rows),
        "items": [
            {
                "run_id": r[0],
                "as_of_date": None if r[1] is None else str(r[1]),
                "model_name": r[2],
                "row_count": r[3],
                "first_created_at": None if r[4] is None else r[4].isoformat(),
                "last_created_at": None if r[5] is None else r[5].isoformat(),
            }
            for r in rows
        ],
    }


@app.get("/predictions/latest", response_model=RunDetailResponse)
def get_latest_predictions():
    return get_latest_run()


@app.get("/predictions/runs/{run_id}", response_model=RunDetailResponse)
def get_predictions_by_run_id(run_id: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    prediction_run_id,
                    as_of_date,
                    model_name,
                    ticker,
                    last_close,
                    pred_close,
                    pred_return,
                    graph_gate,
                    created_at
                FROM stock.inference_predictions
                WHERE prediction_run_id = %s
                ORDER BY ticker ASC
                """,
                (run_id,),
            )
            rows = cur.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"Run id not found: {run_id}")

    first = rows[0]
    return {
        "run_id": run_id,
        "as_of_date": None if first[1] is None else str(first[1]),
        "model_name": first[2],
        "row_count": len(rows),
        "items": [normalize_prediction_row(r) for r in rows],
    }

@app.get("/tickers", response_model=TickersResponse)
def list_tickers():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT ticker
                FROM stock.inference_predictions
                ORDER BY ticker ASC
                """
            )
            rows = cur.fetchall()

    return {"tickers": [r[0] for r in rows]}


@app.get("/dashboard/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH latest_run AS (
                    SELECT prediction_run_id
                    FROM stock.inference_predictions
                    GROUP BY prediction_run_id
                    ORDER BY MAX(created_at) DESC
                    LIMIT 1
                )
                SELECT
                    p.prediction_run_id,
                    MAX(p.model_name) AS model_name,
                    MAX(p.as_of_date) AS as_of_date,
                    COUNT(*) AS row_count,
                    COUNT(DISTINCT p.ticker) AS ticker_count,
                    AVG(p.pred_return) AS avg_pred_return,
                    MAX(p.pred_return) AS max_pred_return,
                    MIN(p.pred_return) AS min_pred_return,
                    MAX(p.created_at) AS last_updated
                FROM stock.inference_predictions p
                JOIN latest_run lr
                  ON p.prediction_run_id = lr.prediction_run_id
                GROUP BY p.prediction_run_id
                """
            )
            row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="No dashboard summary available.")

    return {
        "latest_run_id": row[0],
        "model_name": row[1],
        "as_of_date": None if row[2] is None else str(row[2]),
        "row_count": row[3],
        "ticker_count": row[4],
        "avg_pred_return": None if row[5] is None else float(row[5]),
        "max_pred_return": None if row[6] is None else float(row[6]),
        "min_pred_return": None if row[7] is None else float(row[7]),
        "last_updated": None if row[8] is None else row[8].isoformat(),
    }

@app.get("/predictions/ticker/{ticker}/history", response_model=PredictionHistoryResponse)
def get_ticker_prediction_history(
    ticker: str,
    limit: int = Query(default=30, ge=1, le=200)
):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    prediction_run_id,
                    as_of_date,
                    last_close,
                    pred_close,
                    pred_return,
                    graph_gate,
                    model_name,
                    created_at
                FROM stock.inference_predictions
                WHERE ticker = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (ticker, limit),
            )
            rows = cur.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No prediction history found for ticker: {ticker}")

    return {
        "ticker": ticker,
        "items": [
            {
                "run_id": r[0],
                "as_of_date": None if r[1] is None else str(r[1]),
                "last_close": float(r[2]),
                "pred_close": float(r[3]),
                "pred_return": None if r[4] is None else float(r[4]),
                "graph_gate": None if r[5] is None else float(r[5]),
                "model_name": r[6],
                "created_at": None if r[7] is None else r[7].isoformat(),
            }
            for r in rows
        ],
    }

@app.get("/prices/ticker/{ticker}/history", response_model=PriceHistoryResponse)
def get_ticker_price_history(
    ticker: str,
    days: int = Query(default=30, ge=1, le=365)
):
    csv_path = find_raw_csv_for_ticker(ticker)

    rows = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_value = row.get("Date") or row.get("date")
            close_value = row.get("Close") or row.get("close")
            if date_value and close_value:
                try:
                    rows.append({
                        "date": str(date_value),
                        "close": float(close_value),
                    })
                except ValueError:
                    continue

    if not rows:
        raise HTTPException(status_code=404, detail=f"No price history available for ticker: {ticker}")

    return {
        "ticker": ticker,
        "days": days,
        "items": rows[-days:],
    }