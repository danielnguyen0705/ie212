import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2


def get_pg_conn(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
):
    return psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
    )


def ensure_table(conn):
    with conn:
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS stock;")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS stock.inference_predictions (
                    id BIGSERIAL PRIMARY KEY,
                    prediction_run_id TEXT NOT NULL,
                    as_of_date DATE,
                    model_name TEXT NOT NULL,
                    checkpoint_path TEXT,
                    input_npz_path TEXT,
                    output_json_path TEXT,
                    device TEXT,
                    ticker TEXT NOT NULL,
                    last_close DOUBLE PRECISION NOT NULL,
                    pred_close DOUBLE PRECISION NOT NULL,
                    pred_return DOUBLE PRECISION,
                    graph_gate DOUBLE PRECISION,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (prediction_run_id, ticker)
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_inference_predictions_created_at
                ON stock.inference_predictions (created_at DESC);
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_inference_predictions_ticker
                ON stock.inference_predictions (ticker);
                """
            )


def load_json(json_path: Path) -> dict[str, Any]:
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "predictions" not in data:
        raise KeyError("Missing 'predictions' key in inference JSON")

    if not isinstance(data["predictions"], list) or len(data["predictions"]) == 0:
        raise ValueError("Inference JSON has no prediction rows")

    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-json",
        required=True,
        help="Path to inference output JSON",
    )
    parser.add_argument(
        "--model-name",
        default="hybrid_expanding_best_full",
        help="Logical model name to store in DB",
    )
    parser.add_argument(
        "--prediction-run-id",
        default=None,
        help="Optional custom run id. If omitted, auto-generate.",
    )
    parser.add_argument(
        "--pg-host",
        default="postgres",
        help="PostgreSQL host",
    )
    parser.add_argument(
        "--pg-port",
        type=int,
        default=5432,
        help="PostgreSQL port",
    )
    parser.add_argument(
        "--pg-db",
        default="stock_project",
        help="PostgreSQL database",
    )
    parser.add_argument(
        "--pg-user",
        default="stock_user",
        help="PostgreSQL user",
    )
    parser.add_argument(
        "--pg-password",
        default="change_me_postgres",
        help="PostgreSQL password",
    )
    args = parser.parse_args()

    json_path = Path(args.input_json)
    data = load_json(json_path)

    prediction_run_id = args.prediction_run_id
    if prediction_run_id is None or prediction_run_id.strip() == "":
        prediction_run_id = f"local_inference_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    checkpoint_path = data.get("checkpoint")
    input_npz_path = data.get("input_npz")
    as_of_date = data.get("as_of_date")
    device = data.get("device")
    rows = data["predictions"]

    conn = get_pg_conn(
        host=args.pg_host,
        port=args.pg_port,
        dbname=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
    )

    try:
        ensure_table(conn)

        inserted = 0
        with conn:
            with conn.cursor() as cur:
                for row in rows:
                    cur.execute(
                        """
                        INSERT INTO stock.inference_predictions (
                            prediction_run_id,
                            as_of_date,
                            model_name,
                            checkpoint_path,
                            input_npz_path,
                            output_json_path,
                            device,
                            ticker,
                            last_close,
                            pred_close,
                            pred_return,
                            graph_gate
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (prediction_run_id, ticker)
                        DO UPDATE SET
                            as_of_date = EXCLUDED.as_of_date,
                            model_name = EXCLUDED.model_name,
                            checkpoint_path = EXCLUDED.checkpoint_path,
                            input_npz_path = EXCLUDED.input_npz_path,
                            output_json_path = EXCLUDED.output_json_path,
                            device = EXCLUDED.device,
                            last_close = EXCLUDED.last_close,
                            pred_close = EXCLUDED.pred_close,
                            pred_return = EXCLUDED.pred_return,
                            graph_gate = EXCLUDED.graph_gate,
                            created_at = NOW()
                        """,
                        (
                            prediction_run_id,
                            as_of_date,
                            args.model_name,
                            checkpoint_path,
                            input_npz_path,
                            str(json_path),
                            device,
                            row["ticker"],
                            float(row["last_close"]),
                            float(row["pred_close"]),
                            None if row["pred_return"] is None else float(row["pred_return"]),
                            None if row["graph_gate"] is None else float(row["graph_gate"]),
                        ),
                    )
                    inserted += 1

        print("=" * 80)
        print("Saved inference predictions to PostgreSQL successfully.")
        print(f"prediction_run_id: {prediction_run_id}")
        print(f"rows_written: {inserted}")
        print(f"table: stock.inference_predictions")
        print("=" * 80)

    finally:
        conn.close()


if __name__ == "__main__":
    main()