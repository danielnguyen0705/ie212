from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from ie212_settings import airflow_runtime_env, get_pg_conn


RUNTIME_ENV = airflow_runtime_env()


def validate_inference_predictions():
    conn = get_pg_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = 'stock'
                          AND table_name = 'inference_predictions'
                    )
                    """
                )
                exists = cur.fetchone()[0]
                if not exists:
                    raise ValueError("Table stock.inference_predictions does not exist.")

                cur.execute("SELECT COUNT(*) FROM stock.inference_predictions;")
                total_count = cur.fetchone()[0]
                if total_count <= 0:
                    raise ValueError("stock.inference_predictions has no rows.")

                cur.execute(
                    """
                    SELECT prediction_run_id, COUNT(*)
                    FROM stock.inference_predictions
                    GROUP BY prediction_run_id
                    ORDER BY MAX(created_at) DESC
                    LIMIT 1
                    """
                )
                latest = cur.fetchone()
                if latest is None:
                    raise ValueError("Could not find latest prediction_run_id.")

        print(f"Latest prediction_run_id = {latest[0]}, rows = {latest[1]}")
    finally:
        conn.close()


with DAG(
    dag_id="ie212_end_to_end_inference_pipeline",
    schedule=None,
    start_date=datetime(2026, 4, 15),
    catchup=False,
    tags=["ie212", "inference", "end-to-end"],
) as dag:
    build_latest_bundle = BashOperator(
        task_id="build_latest_bundle",
        env=RUNTIME_ENV,
        bash_command=r"""
set -e
docker exec "$IE212_ML_RUNNER_CONTAINER" \
  python -m scripts.build_latest_inference_bundle \
  --data-dir "$IE212_INFERENCE_RAW_DIR" \
  --output "$IE212_INFERENCE_BUNDLE_PATH"
""",
    )

    run_checkpoint_inference = BashOperator(
        task_id="run_checkpoint_inference",
        env=RUNTIME_ENV,
        bash_command=r"""
set -e
docker exec "$IE212_ML_RUNNER_CONTAINER" \
  python -m scripts.run_checkpoint_inference \
  --checkpoint "$IE212_MODEL_CHECKPOINT" \
  --input-npz "$IE212_INFERENCE_BUNDLE_PATH" \
  --output-json "$IE212_INFERENCE_OUTPUT_JSON" \
  --device cpu
""",
    )

    save_inference_to_postgres = BashOperator(
        task_id="save_inference_to_postgres",
        env=RUNTIME_ENV,
        bash_command=r"""
set -e
docker exec "$IE212_ML_RUNNER_CONTAINER" \
  python -m scripts.save_inference_to_postgres \
  --input-json "$IE212_INFERENCE_OUTPUT_JSON" \
  --model-name "$IE212_MODEL_NAME" \
  --pg-host "$IE212_POSTGRES_HOST" \
  --pg-port "$IE212_POSTGRES_PORT" \
  --pg-db "$IE212_POSTGRES_DB" \
  --pg-user "$IE212_POSTGRES_USER" \
  --pg-password "$IE212_POSTGRES_PASSWORD"
""",
    )

    validate_db_rows = PythonOperator(
        task_id="validate_inference_predictions",
        python_callable=validate_inference_predictions,
    )

    build_latest_bundle >> run_checkpoint_inference >> save_inference_to_postgres >> validate_db_rows