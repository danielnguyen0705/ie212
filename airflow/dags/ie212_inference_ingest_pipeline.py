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

        print(f"stock.inference_predictions row count = {total_count}")
    finally:
        conn.close()


with DAG(
    dag_id="ie212_inference_ingest_pipeline",
    schedule=None,
    start_date=datetime(2026, 4, 15),
    catchup=False,
    tags=["ie212", "inference", "postgres", "ingest"],
) as dag:
    ingest_latest_prediction_json = BashOperator(
        task_id="ingest_latest_prediction_json",
        env=RUNTIME_ENV,
        bash_command=r"""
set -e
python /opt/airflow/project_scripts/save_inference_to_postgres.py \
  --input-json /opt/airflow/project_outputs/inference/latest_prediction.json \
  --model-name hybrid_expanding_best_full \
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

    ingest_latest_prediction_json >> validate_db_rows