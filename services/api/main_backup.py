from pathlib import Path
import os
from contextlib import contextmanager
from typing import Any

import psycopg2
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse


APP_TITLE = "IE212 Prediction API"
APP_VERSION = "1.1.0"

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


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


@app.get("/predictions/runs/latest")
def get_latest_run_metadata():
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
                LIMIT 1
                """
            )
            row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="No prediction runs found.")

    return {
        "prediction_run_id": row[0],
        "as_of_date": None if row[1] is None else str(row[1]),
        "model_name": row[2],
        "row_count": row[3],
        "first_created_at": None if row[4] is None else row[4].isoformat(),
        "last_created_at": None if row[5] is None else row[5].isoformat(),
    }


@app.get("/predictions/runs/recent")
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
                "prediction_run_id": r[0],
                "as_of_date": None if r[1] is None else str(r[1]),
                "model_name": r[2],
                "row_count": r[3],
                "first_created_at": None if r[4] is None else r[4].isoformat(),
                "last_created_at": None if r[5] is None else r[5].isoformat(),
            }
            for r in rows
        ],
    }


@app.get("/predictions/latest")
def get_latest_predictions(limit: int = Query(default=50, ge=1, le=500)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT prediction_run_id
                FROM stock.inference_predictions
                GROUP BY prediction_run_id
                ORDER BY MAX(created_at) DESC
                LIMIT 1
                """
            )
            latest_run = cur.fetchone()

            if latest_run is None:
                raise HTTPException(status_code=404, detail="No prediction runs found.")

            prediction_run_id = latest_run[0]

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
                LIMIT %s
                """,
                (prediction_run_id, limit),
            )
            rows = cur.fetchall()

    return {
        "prediction_run_id": prediction_run_id,
        "count": len(rows),
        "items": [
            {
                "prediction_run_id": r[0],
                "as_of_date": None if r[1] is None else str(r[1]),
                "model_name": r[2],
                "ticker": r[3],
                "last_close": float(r[4]),
                "pred_close": float(r[5]),
                "pred_return": None if r[6] is None else float(r[6]),
                "graph_gate": None if r[7] is None else float(r[7]),
                "created_at": None if r[8] is None else r[8].isoformat(),
            }
            for r in rows
        ],
    }


@app.get("/predictions/runs/{run_id}")
def get_predictions_by_run_id(run_id: str, limit: int = Query(default=500, ge=1, le=2000)):
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
                LIMIT %s
                """,
                (run_id, limit),
            )
            rows = cur.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"Run id not found: {run_id}")

    return {
        "prediction_run_id": run_id,
        "count": len(rows),
        "items": [
            {
                "prediction_run_id": r[0],
                "as_of_date": None if r[1] is None else str(r[1]),
                "model_name": r[2],
                "ticker": r[3],
                "last_close": float(r[4]),
                "pred_close": float(r[5]),
                "pred_return": None if r[6] is None else float(r[6]),
                "graph_gate": None if r[7] is None else float(r[7]),
                "created_at": None if r[8] is None else r[8].isoformat(),
            }
            for r in rows
        ],
    }