import os
import psycopg2


def env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and (value is None or str(value).strip() == ""):
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_pg_conn(dbname: str | None = None):
    return psycopg2.connect(
        host=env("IE212_POSTGRES_HOST", "postgres"),
        port=int(env("IE212_POSTGRES_PORT", "5432")),
        dbname=dbname or env("IE212_POSTGRES_DB", "stock_project"),
        user=env("IE212_POSTGRES_USER", "stock_user"),
        password=env("IE212_POSTGRES_PASSWORD", "change_me_postgres"),
    )


def airflow_runtime_env() -> dict[str, str]:
    keys = [
        "IE212_POSTGRES_HOST",
        "IE212_POSTGRES_PORT",
        "IE212_POSTGRES_DB",
        "IE212_POSTGRES_USER",
        "IE212_POSTGRES_PASSWORD",
        "IE212_KAFKA_BOOTSTRAP_SERVERS",
        "IE212_KAFKA_TOPIC",
        "IE212_SPARK_MASTER_CONTAINER",
        "IE212_SPARK_MASTER_URL",
        "IE212_SPARK_MASTER_UI_URL",
        "IE212_SPARK_KAFKA_PACKAGE",
        "IE212_POSTGRES_JDBC_PACKAGE",
        "IE212_MINIO_CLIENT_CONTAINER",
        "IE212_MINIO_ENDPOINT",
        "IE212_MINIO_ACCESS_KEY",
        "IE212_MINIO_SECRET_KEY",
        "IE212_MINIO_PROCESSED_BUCKET",
        "IE212_MINIO_PARQUET_PREFIX",
        "IE212_PARQUET_LOCAL_DIR",
        "IE212_SPARK_PARQUET_DIRNAME",
        "IE212_ML_LOCAL_PARQUET_DIR",
        "IE212_ML_RUNNER_CONTAINER",
        "IE212_MODEL_CHECKPOINT",
        "IE212_MODEL_NAME",
        "IE212_INFERENCE_RAW_DIR",
        "IE212_INFERENCE_BUNDLE_PATH",
        "IE212_INFERENCE_OUTPUT_JSON",
    ]
    return {k: env(k, "") for k in keys}
