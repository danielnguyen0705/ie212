import os
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from ie212_settings import env, get_pg_conn, airflow_runtime_env


PARQUET_DIR = env("IE212_PARQUET_LOCAL_DIR", "/opt/airflow/shared/spark_out/kafka_ticks_parquet")
RUNTIME_ENV = airflow_runtime_env()


def validate_batch_postgres():
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
                    raise ValueError("stock.kafka_ticks_batch has no rows.")

        print(f"stock.kafka_ticks_batch row count = {count}")
    finally:
        conn.close()


def validate_local_parquet():
    if not os.path.isdir(PARQUET_DIR):
        raise ValueError(f"Directory not found: {PARQUET_DIR}")

    files = os.listdir(PARQUET_DIR)
    parquet_files = [f for f in files if f.endswith(".parquet")]
    has_success = "_SUCCESS" in files

    if len(parquet_files) <= 0:
        raise ValueError("No parquet file found in local Spark output.")

    if not has_success:
        raise ValueError("Missing _SUCCESS marker in local Spark output.")

    print(f"Local parquet ok. parquet_files={len(parquet_files)}, has_success={has_success}")


def write_audit(**context):
    files = os.listdir(PARQUET_DIR)
    parquet_files = [f for f in files if f.endswith(".parquet")]
    has_success = "_SUCCESS" in files
    run_id = context["dag_run"].run_id

    conn = get_pg_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM stock.kafka_ticks;")
                kafka_ticks_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM stock.kafka_ticks_batch;")
                batch_count = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO stock.pipeline_audit (
                        run_id,
                        kafka_ok,
                        spark_ok,
                        minio_ok,
                        postgres_ok,
                        parquet_local_ok,
                        kafka_ticks_count,
                        parquet_files_count,
                        has_success_marker,
                        missing_tables,
                        notes
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        run_id,
                        True,
                        True,
                        True,
                        True,
                        True,
                        int(kafka_ticks_count),
                        int(len(parquet_files)),
                        bool(has_success),
                        "",
                        f"spark_exec_pipeline ok | batch_table_count={batch_count}",
                    ),
                )
        print("Audit row inserted for ie212_spark_exec_pipeline")
    finally:
        conn.close()


with DAG(
    dag_id="ie212_spark_exec_pipeline",
    schedule=None,
    start_date=datetime(2026, 4, 15),
    catchup=False,
    tags=["ie212", "spark", "orchestration", "exec"],
) as dag:
    spark_batch_to_postgres = BashOperator(
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

    validate_batch_db = PythonOperator(
        task_id="validate_batch_postgres",
        python_callable=validate_batch_postgres,
    )

    spark_batch_to_parquet = BashOperator(
        task_id="spark_batch_to_parquet",
        env=RUNTIME_ENV,
        bash_command=r"""
set -e
docker exec "$IE212_SPARK_MASTER_CONTAINER" \
  /opt/spark/bin/spark-submit \
  --master "$IE212_SPARK_MASTER_URL" \
  --packages "$IE212_SPARK_KAFKA_PACKAGE" \
  /opt/spark/jobs/write_kafka_batch_to_parquet.py
""",
    )

    validate_parquet = PythonOperator(
        task_id="validate_local_parquet",
        python_callable=validate_local_parquet,
    )

    upload_parquet_to_minio = BashOperator(
        task_id="upload_parquet_to_minio",
        env=RUNTIME_ENV,
        bash_command=r"""
set -e
docker exec "$IE212_MINIO_CLIENT_CONTAINER" \
  mc alias set local "$IE212_MINIO_ENDPOINT" "$IE212_MINIO_ACCESS_KEY" "$IE212_MINIO_SECRET_KEY"

docker exec "$IE212_MINIO_CLIENT_CONTAINER" \
  mc rm --recursive --force "local/$IE212_MINIO_PROCESSED_BUCKET/$IE212_MINIO_PARQUET_PREFIX" || true

docker exec "$IE212_MINIO_CLIENT_CONTAINER" \
  mc cp --recursive "/upload/$IE212_SPARK_PARQUET_DIRNAME" "local/$IE212_MINIO_PROCESSED_BUCKET/$IE212_MINIO_PARQUET_PREFIX"
""",
    )

    write_pipeline_audit = PythonOperator(
        task_id="write_pipeline_audit",
        python_callable=write_audit,
    )

    spark_batch_to_postgres >> validate_batch_db
    validate_batch_db >> spark_batch_to_parquet >> validate_parquet >> upload_parquet_to_minio >> write_pipeline_audit