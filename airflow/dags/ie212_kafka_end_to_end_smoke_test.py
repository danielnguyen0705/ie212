from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from ie212_settings import airflow_runtime_env, get_pg_conn


RUNTIME_ENV = airflow_runtime_env()
PRODUCER_CONTAINER = "ie212-stock-producer"


def validate_kafka_batch_table():
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
                          AND table_name = 'kafka_ticks_batch'
                    )
                    """
                )
                exists = cur.fetchone()[0]
                if not exists:
                    raise ValueError("Table stock.kafka_ticks_batch does not exist.")

                cur.execute("SELECT COUNT(*) FROM stock.kafka_ticks_batch;")
                count = cur.fetchone()[0]
                if count <= 0:
                    raise ValueError("stock.kafka_ticks_batch has no rows after producer smoke test.")

        print(f"Kafka smoke test wrote batch rows successfully. row_count={count}")
    finally:
        conn.close()


with DAG(
    dag_id="ie212_kafka_end_to_end_smoke_test",
    schedule=None,
    start_date=datetime(2026, 4, 17),
    catchup=False,
    tags=["ie212", "kafka", "smoke-test", "end-to-end"],
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

    validate_batch_rows = PythonOperator(
        task_id="validate_kafka_batch_table",
        python_callable=validate_kafka_batch_table,
    )

    publish_one_round >> kafka_batch_to_postgres >> validate_batch_rows
