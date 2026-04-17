import os
import socket
import urllib.request
from datetime import datetime

import psycopg2

from airflow import DAG
from airflow.operators.python import PythonOperator


PG_HOST = "postgres"
PG_PORT = 5432
PG_DB = "stock_project"
PG_USER = "stock_user"
PG_PASSWORD = "change_me_postgres"

PARQUET_DIR = "/opt/airflow/shared/spark_out/kafka_ticks_parquet"


def get_pg_conn():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
    )


def ensure_audit_table():
    conn = get_pg_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("CREATE SCHEMA IF NOT EXISTS stock;")
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS stock.pipeline_audit (
                        id BIGSERIAL PRIMARY KEY,
                        run_id TEXT NOT NULL,
                        checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        kafka_ok BOOLEAN NOT NULL DEFAULT FALSE,
                        spark_ok BOOLEAN NOT NULL DEFAULT FALSE,
                        minio_ok BOOLEAN NOT NULL DEFAULT FALSE,
                        postgres_ok BOOLEAN NOT NULL DEFAULT FALSE,
                        parquet_local_ok BOOLEAN NOT NULL DEFAULT FALSE,
                        kafka_ticks_count INTEGER NOT NULL DEFAULT 0,
                        parquet_files_count INTEGER NOT NULL DEFAULT 0,
                        has_success_marker BOOLEAN NOT NULL DEFAULT FALSE,
                        missing_tables TEXT,
                        notes TEXT
                    );
                    """
                )

                cur.execute(
                    "ALTER TABLE stock.pipeline_audit ADD COLUMN IF NOT EXISTS parquet_local_ok BOOLEAN NOT NULL DEFAULT FALSE;"
                )
                cur.execute(
                    "ALTER TABLE stock.pipeline_audit ADD COLUMN IF NOT EXISTS parquet_files_count INTEGER NOT NULL DEFAULT 0;"
                )
                cur.execute(
                    "ALTER TABLE stock.pipeline_audit ADD COLUMN IF NOT EXISTS has_success_marker BOOLEAN NOT NULL DEFAULT FALSE;"
                )
        print("Audit table is ready.")
    finally:
        conn.close()


def check_kafka():
    try:
        with socket.create_connection(("kafka", 9092), timeout=5):
            return {"kafka_ok": True, "error": None}
    except Exception as e:
        return {"kafka_ok": False, "error": str(e)}


def check_spark_master():
    try:
        with urllib.request.urlopen("http://spark-master:8080", timeout=5) as resp:
            ok = resp.status == 200
            return {"spark_ok": ok, "error": None if ok else f"HTTP {resp.status}"}
    except Exception as e:
        return {"spark_ok": False, "error": str(e)}


def check_minio():
    try:
        with urllib.request.urlopen("http://minio:9000/minio/health/live", timeout=5) as resp:
            body = resp.read().decode("utf-8", errors="ignore").strip()
            ok = (resp.status == 200) and ("OK" in body or body == "")
            return {
                "minio_ok": ok,
                "error": None if ok else f"HTTP {resp.status}, body={body}",
            }
    except Exception as e:
        return {"minio_ok": False, "error": str(e)}


def check_postgres():
    conn = get_pg_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'stock'
                    """
                )
                existing_tables = {row[0] for row in cur.fetchall()}
                required_tables = {
                    "predictions",
                    "model_registry",
                    "kafka_ticks_batch",
                    "pipeline_audit",
                }
                missing_tables = sorted(list(required_tables - existing_tables))

                cur.execute("SELECT COUNT(*) FROM stock.kafka_ticks_batch;")
                kafka_batch_count = cur.fetchone()[0]

        return {
            "postgres_ok": len(missing_tables) == 0,
            "kafka_batch_count": int(kafka_batch_count),
            "missing_tables": missing_tables,
            "error": None,
        }
    except Exception as e:
        return {
            "postgres_ok": False,
            "kafka_batch_count": 0,
            "missing_tables": ["unknown"],
            "error": str(e),
        }
    finally:
        conn.close()


def check_parquet_local():
    try:
        if not os.path.isdir(PARQUET_DIR):
            return {
                "parquet_local_ok": False,
                "parquet_files_count": 0,
                "has_success_marker": False,
                "error": f"Directory not found: {PARQUET_DIR}",
            }

        files = os.listdir(PARQUET_DIR)
        parquet_files = [f for f in files if f.endswith(".parquet")]
        has_success_marker = "_SUCCESS" in files

        ok = len(parquet_files) > 0 and has_success_marker

        return {
            "parquet_local_ok": ok,
            "parquet_files_count": len(parquet_files),
            "has_success_marker": has_success_marker,
            "error": None if ok else f"parquet_files={len(parquet_files)}, success_marker={has_success_marker}",
        }
    except Exception as e:
        return {
            "parquet_local_ok": False,
            "parquet_files_count": 0,
            "has_success_marker": False,
            "error": str(e),
        }


def write_audit(**context):
    ti = context["ti"]
    run_id = context["dag_run"].run_id

    kafka_result = ti.xcom_pull(task_ids="check_kafka")
    spark_result = ti.xcom_pull(task_ids="check_spark_master")
    minio_result = ti.xcom_pull(task_ids="check_minio")
    postgres_result = ti.xcom_pull(task_ids="check_postgres")
    parquet_result = ti.xcom_pull(task_ids="check_parquet_local")

    notes = []
    if kafka_result and kafka_result.get("error"):
        notes.append(f"kafka_error={kafka_result['error']}")
    if spark_result and spark_result.get("error"):
        notes.append(f"spark_error={spark_result['error']}")
    if minio_result and minio_result.get("error"):
        notes.append(f"minio_error={minio_result['error']}")
    if postgres_result and postgres_result.get("error"):
        notes.append(f"postgres_error={postgres_result['error']}")
    if parquet_result and parquet_result.get("error"):
        notes.append(f"parquet_error={parquet_result['error']}")

    conn = get_pg_conn()
    try:
        with conn:
            with conn.cursor() as cur:
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
                        bool(kafka_result.get("kafka_ok", False)),
                        bool(spark_result.get("spark_ok", False)),
                        bool(minio_result.get("minio_ok", False)),
                        bool(postgres_result.get("postgres_ok", False)),
                        bool(parquet_result.get("parquet_local_ok", False)),
                        int(postgres_result.get("kafka_batch_count", 0)),
                        int(parquet_result.get("parquet_files_count", 0)),
                        bool(parquet_result.get("has_success_marker", False)),
                        ",".join(postgres_result.get("missing_tables", [])),
                        " | ".join(notes) if notes else "all checks completed",
                    ),
                )
        print("Audit row inserted into stock.pipeline_audit")
    finally:
        conn.close()


def validate_pipeline(**context):
    ti = context["ti"]

    kafka_result = ti.xcom_pull(task_ids="check_kafka")
    spark_result = ti.xcom_pull(task_ids="check_spark_master")
    minio_result = ti.xcom_pull(task_ids="check_minio")
    postgres_result = ti.xcom_pull(task_ids="check_postgres")
    parquet_result = ti.xcom_pull(task_ids="check_parquet_local")

    errors = []

    if not kafka_result.get("kafka_ok", False):
        errors.append(f"Kafka check failed: {kafka_result.get('error')}")

    if not spark_result.get("spark_ok", False):
        errors.append(f"Spark check failed: {spark_result.get('error')}")

    if not minio_result.get("minio_ok", False):
        errors.append(f"MinIO check failed: {minio_result.get('error')}")

    if not postgres_result.get("postgres_ok", False):
        errors.append(
            f"PostgreSQL/table check failed: missing={postgres_result.get('missing_tables')}, error={postgres_result.get('error')}"
        )

    if int(postgres_result.get("kafka_batch_count", 0)) <= 0:
        errors.append("stock.kafka_ticks_batch currently has no rows")

    if not parquet_result.get("parquet_local_ok", False):
        errors.append(f"Parquet output check failed: {parquet_result.get('error')}")

    if int(parquet_result.get("parquet_files_count", 0)) <= 0:
        errors.append("No parquet files found in Spark output directory")

    if not parquet_result.get("has_success_marker", False):
        errors.append("Missing _SUCCESS marker in Spark output directory")

    if errors:
        raise ValueError(" | ".join(errors))

    print("IE212 full validation pipeline passed for Kafka batch path.")


with DAG(
    dag_id="ie212_full_validation_pipeline",
    schedule=None,
    start_date=datetime(2026, 4, 15),
    catchup=False,
    tags=["ie212", "pipeline", "validation", "full"],
) as dag:
    t1 = PythonOperator(
        task_id="ensure_audit_table",
        python_callable=ensure_audit_table,
    )

    t2 = PythonOperator(
        task_id="check_kafka",
        python_callable=check_kafka,
    )

    t3 = PythonOperator(
        task_id="check_spark_master",
        python_callable=check_spark_master,
    )

    t4 = PythonOperator(
        task_id="check_minio",
        python_callable=check_minio,
    )

    t5 = PythonOperator(
        task_id="check_postgres",
        python_callable=check_postgres,
    )

    t6 = PythonOperator(
        task_id="check_parquet_local",
        python_callable=check_parquet_local,
    )

    t7 = PythonOperator(
        task_id="write_audit",
        python_callable=write_audit,
    )

    t8 = PythonOperator(
        task_id="validate_pipeline",
        python_callable=validate_pipeline,
    )

    t1 >> [t2, t3, t4, t5, t6] >> t7 >> t8
