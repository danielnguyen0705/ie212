import os
from datetime import datetime

import psycopg2

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator


PG_HOST = "postgres"
PG_PORT = 5432
PG_DB = "stock_project"
PG_USER = "stock_user"
PG_PASSWORD = "change_me_postgres"

PARQUET_DIR = "/opt/airflow/shared/spark_out/kafka_ticks_parquet"
COMPOSE_NETWORK = "ie212-bigdata_bigdata_net"


def get_pg_conn():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
    )


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


def write_audit():
    files = os.listdir(PARQUET_DIR)
    parquet_files = [f for f in files if f.endswith(".parquet")]
    has_success = "_SUCCESS" in files

    conn = get_pg_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM stock.kafka_ticks;")
                kafka_ticks_count = cur.fetchone()[0]

                cur.execute(
                    """
                    SELECT COUNT(*) FROM stock.kafka_ticks_batch;
                    """
                )
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
                        "ie212_spark_exec_pipeline_manual",
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
        bash_command=(
            "docker exec ie212-spark-master "
            "/opt/spark/bin/spark-submit "
            "--master spark://spark-master:7077 "
            "--packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2,org.postgresql:postgresql:42.7.10 "
            "/opt/spark/jobs/write_kafka_batch_to_postgres.py"
        ),
    )

    validate_batch_db = PythonOperator(
        task_id="validate_batch_postgres",
        python_callable=validate_batch_postgres,
    )

    spark_batch_to_parquet = BashOperator(
        task_id="spark_batch_to_parquet",
        bash_command=(
            "docker exec ie212-spark-master "
            "/opt/spark/bin/spark-submit "
            "--master spark://spark-master:7077 "
            "--packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2 "
            "/opt/spark/jobs/write_kafka_batch_to_parquet.py"
        ),
    )

    validate_parquet = PythonOperator(
        task_id="validate_local_parquet",
        python_callable=validate_local_parquet,
    )

    upload_parquet_to_minio = BashOperator(
        task_id="upload_parquet_to_minio",
        bash_command=(
            "docker exec ie212-minio-client sh -lc "
            "\"mc alias set local http://minio:9000 minioadmin change_me_minio && "
            "mc rm --recursive --force local/processed/kafka_ticks_parquet || true && "
            "mc cp --recursive /upload/kafka_ticks_parquet local/processed/kafka_ticks_parquet\""
        ),
    )

    write_pipeline_audit = PythonOperator(
        task_id="write_pipeline_audit",
        python_callable=write_audit,
    )

    spark_batch_to_postgres >> validate_batch_db
    validate_batch_db >> spark_batch_to_parquet >> validate_parquet >> upload_parquet_to_minio >> write_pipeline_audit