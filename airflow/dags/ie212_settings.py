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
    defaults = {
        "IE212_POSTGRES_HOST": "postgres",
        "IE212_POSTGRES_PORT": "5432",
        "IE212_POSTGRES_DB": "stock_project",
        "IE212_POSTGRES_USER": "stock_user",
        "IE212_POSTGRES_PASSWORD": "change_me_postgres",
        "IE212_KAFKA_BOOTSTRAP_SERVERS": "kafka:9092",
        "IE212_KAFKA_TOPIC": "stock-price",
        "IE212_SPARK_MASTER_CONTAINER": "ie212-spark-master",
        "IE212_SPARK_MASTER_URL": "spark://spark-master:7077",
        "IE212_SPARK_MASTER_UI_URL": "http://spark-master:8080",
        "IE212_SPARK_KAFKA_PACKAGE": "org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2",
        "IE212_POSTGRES_JDBC_PACKAGE": "org.postgresql:postgresql:42.7.10",
        "IE212_MINIO_CLIENT_CONTAINER": "ie212-minio-client",
        "IE212_MINIO_ENDPOINT": "http://minio:9000",
        "IE212_MINIO_ACCESS_KEY": "minioadmin",
        "IE212_MINIO_SECRET_KEY": "change_me_minio",
        "IE212_MINIO_PROCESSED_BUCKET": "processed",
        "IE212_MINIO_PARQUET_PREFIX": "kafka_ticks_parquet",
        "IE212_PARQUET_LOCAL_DIR": "/opt/airflow/shared/spark_out/kafka_ticks_parquet",
        "IE212_SPARK_PARQUET_DIRNAME": "kafka_ticks_parquet",
        "IE212_ML_LOCAL_PARQUET_DIR": "/workspace/services/spark/out/kafka_ticks_parquet",
        "IE212_ML_RUNNER_CONTAINER": "ie212-ml-infer",
        "IE212_MODEL_CHECKPOINT": "/workspace/models/hybrid_expanding_best_full.pt",
        "IE212_MODEL_NAME": "hybrid_expanding_best_full",
        "IE212_INFERENCE_RAW_DIR": "/workspace/data/raw",
        "IE212_INFERENCE_BUNDLE_PATH": "/workspace/data/inference/latest_window.npz",
        "IE212_INFERENCE_OUTPUT_JSON": "/workspace/outputs/inference/latest_prediction.json",
    }
    return {k: env(k, v) for k, v in defaults.items()}
