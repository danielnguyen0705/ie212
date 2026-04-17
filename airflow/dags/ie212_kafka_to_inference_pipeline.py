from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from ie212_settings import airflow_runtime_env, get_pg_conn


RUNTIME_ENV = airflow_runtime_env()
PRODUCER_CONTAINER = "ie212-stock-producer"


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
                    raise ValueError("No inference predictions found after Kafka-driven pipeline.")

                cur.execute("SELECT COUNT(*) FROM stock.kafka_ticks_batch;")
                kafka_batch_count = cur.fetchone()[0]
                if kafka_batch_count <= 0:
                    raise ValueError("stock.kafka_ticks_batch has no rows after Kafka-driven pipeline.")

        print(
            f"Kafka-to-inference pipeline succeeded. "
            f"latest_prediction_run_id={latest[0]}, prediction_rows={latest[1]}, kafka_batch_rows={kafka_batch_count}"
        )
    finally:
        conn.close()


with DAG(
    dag_id="ie212_kafka_to_inference_pipeline",
    schedule=None,
    start_date=datetime(2026, 4, 17),
    catchup=False,
    tags=["ie212", "kafka", "inference", "end-to-end"],
) as dag:
    publish_one_round = BashOperator(
        task_id="publish_one_round_to_kafka",
        env=RUNTIME_ENV,
        bash_command=rf"""
set -e
docker exec "{PRODUCER_CONTAINER}" \
  python scripts/publish_stock_ticks.py \
  --bootstrap-servers "$IE212_KAFKA_BOOTSTRAP_SERVERS" \
  --topic "$IE212_KAFKA_TOPIC" \
  --source auto \
  --max-iterations 1 \
  --interval-seconds 0
""",
    )

    kafka_batch_to_postgres = BashOperator(
        task_id="spark_batch_to_postgres",
        env=RUNTIME_ENV,
        bash_command=r"""
set -e
docker exec "$IE212_SPARK_MASTER_CONTAINER" \
  /opt/spark/bin/spark-submit \
  --master "$IE212_SPARK_MASTER_URL" \
  --packages "$IE212_SPARK_KAFKA_PACKAGE,$IE212_POSTGRES_JDBC_PACKAGE" \
  /opt/spark/jobs/write_kafka_batch_to_postgres.py
""",
    )

    build_kafka_bundle = BashOperator(
        task_id="build_kafka_inference_bundle",
        env=RUNTIME_ENV,
        bash_command=r"""
set -e
docker exec "$IE212_ML_RUNNER_CONTAINER" \
  python -m scripts.build_kafka_inference_bundle \
  --data-dir "$IE212_INFERENCE_RAW_DIR" \
  --output "$IE212_INFERENCE_BUNDLE_PATH" \
  --pg-host "$IE212_POSTGRES_HOST" \
  --pg-port "$IE212_POSTGRES_PORT" \
  --pg-db "$IE212_POSTGRES_DB" \
  --pg-user "$IE212_POSTGRES_USER" \
  --pg-password "$IE212_POSTGRES_PASSWORD"
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
  --model-name "$IE212_MODEL_NAME-kafka" \
  --prediction-run-id "kafka_inference_$(date +%Y%m%d_%H%M%S)" \
  --pg-host "$IE212_POSTGRES_HOST" \
  --pg-port "$IE212_POSTGRES_PORT" \
  --pg-db "$IE212_POSTGRES_DB" \
  --pg-user "$IE212_POSTGRES_USER" \
  --pg-password "$IE212_POSTGRES_PASSWORD"
""",
    )

    validate_outputs = PythonOperator(
        task_id="validate_inference_predictions",
        python_callable=validate_inference_predictions,
    )

    publish_one_round >> kafka_batch_to_postgres >> build_kafka_bundle
    build_kafka_bundle >> run_checkpoint_inference >> save_inference_to_postgres >> validate_outputs
