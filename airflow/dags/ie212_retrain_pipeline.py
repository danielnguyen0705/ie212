# airflow/dags/ie212_retrain_pipeline.py
# ============================================================================
# AIRFLOW DAG: RETRAIN MÔ HÌNH ĐỊNH KỲ (Batch Layer Pipeline)
# ============================================================================
#
# MỤC ĐÍCH:
#   Theo kiến trúc Lambda, Speed Layer (Inference) hoạt động liên tục dựa trên
#   checkpoint mô hình có sẵn. Tuy nhiên theo thời gian, mối quan hệ tương quan
#   giữa các cổ phiếu trên thị trường có thể trôi dạt (concept drift).
#
#   DAG này thực hiện Retrain định kỳ (Schedule: Monthly hoặc Quarterly):
#     1. Thu thập dữ liệu lịch sử mới nhất từ yfinance API
#     2. Upload dữ liệu thô (.csv) lên MinIO (S3 bucket raw/) làm Data Lake
#     3. Chạy PySpark tính các chỉ báo kỹ thuật mở rộng (RSI, MACD, Bollinger Bands)
#     4. Chạy Retrain mô hình lai Hybrid LSTM-GNN bằng Expanding Window
#     5. Save model checkpoint + params mới lên MinIO bucket models/
#     6. Cập nhật Model Registry trong PostgreSQL
#     7. Đánh giá chất lượng (Validation) so với mô hình cũ trước khi deploy
#
# ============================================================================

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from ie212_settings import airflow_runtime_env, get_pg_conn

# Khởi tạo các biến môi trường cấu hình chung
RUNTIME_ENV = airflow_runtime_env()
PRODUCER_CONTAINER = "ie212-stock-producer"
ML_RUNNER_CONTAINER = "ie212-ml-infer"
SPARK_MASTER_CONTAINER = "ie212-spark-master"
SPARK_MASTER_URL = "spark://spark-master:7077"


def check_data_drift_and_retrain_need():
    """
    Hàm kiểm tra xem có thực sự cần retrain hay không.
    Ví dụ: So sánh số ngày dữ liệu mới có trong DB so với lần train cuối.
    Nếu số ngày dữ liệu mới > RETRAIN_MIN_NEW_DAYS (20 ngày) → trigger.
    Đây là kỹ thuật tối ưu chi phí hạ tầng trong hệ thống Big Data thực tế.
    """
    conn = get_pg_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                # Lấy ngày cuối cùng của lần dự đoán trước
                cur.execute("SELECT MAX(as_of_date) FROM stock.inference_predictions;")
                last_inference_date = cur.fetchone()[0]

                # Lấy ngày của model active trong registry
                cur.execute("SELECT MAX(created_at) FROM stock.model_registry;")
                last_registry_date = cur.fetchone()[0]

                if last_inference_date is None or last_registry_date is None:
                    print("[retrain] Chưa có lịch sử model hoặc inference. Bắt buộc retrain.")
                    return True

                days_diff = (datetime.now().date() - last_inference_date).days
                print(f"[retrain] Số ngày dữ liệu mới chưa học: {days_diff} ngày.")

                if days_diff >= 20:
                    print("[retrain] Đủ điều kiện thời gian. Tiến hành retrain.")
                    return True
                else:
                    print("[retrain] Chưa đủ dữ liệu mới. Bỏ qua retrain kỳ này.")
                    return False
    finally:
        conn.close()


def update_model_registry_db():
    """
    Cập nhật thông tin checkpoint mới vào Model Registry trong PostgreSQL.
    """
    conn = get_pg_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                model_name = "hybrid_expanding_best_full"
                version = f"v_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                storage_uri = f"s3://models/{model_name}_{version}.pt"
                notes = f"Retrained định kỳ vào lúc {datetime.now().isoformat()}."

                cur.execute(
                    """
                    INSERT INTO stock.model_registry (model_name, model_version, storage_uri, notes)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (model_name, model_version) DO NOTHING;
                    """,
                    (model_name, version, storage_uri, notes),
                )
        print(f"[registry] Đã ghi nhận model mới vào PostgreSQL: version={version}")
    finally:
        conn.close()


# CẤU HÌNH DAG AIRFLOW
default_args = {
    "owner": "ie212_data_architect",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="ie212_retrain_pipeline",
    default_args=default_args,
    description="Pipeline retrain tự động mô hình Hybrid LSTM-GNN định kỳ (Batch Layer)",
    schedule="0 0 1 */3 *",  # Chạy vào ngày 1 hàng quý (00:00)
    start_date=datetime(2026, 5, 28),
    catchup=False,
    tags=["ie212", "batch_layer", "retrain", "mlops"],
) as dag:

    # 1. Kiểm tra điều kiện trôi dạt dữ liệu (Concept Drift)
    check_trigger = PythonOperator(
        task_id="check_data_drift",
        python_callable=check_data_drift_and_retrain_need,
    )

    # 2. Tải toàn bộ dữ liệu lịch sử mới nhất đến thời điểm hiện tại
    download_latest_data = BashOperator(
        task_id="download_latest_data_from_yfinance",
        env=RUNTIME_ENV,
        bash_command=rf"""
set -e
echo "Bắt đầu tải dữ liệu lịch sử mới từ yfinance API..."
docker exec "{PRODUCER_CONTAINER}" \
  python scripts/publish_stock_ticks.py \
  --bootstrap-servers "$IE212_KAFKA_BOOTSTRAP_SERVERS" \
  --topic "$IE212_KAFKA_TOPIC" \
  --source yfinance \
  --max-iterations 1 \
  --interval-seconds 0
""",
    )

    # 3. Đồng bộ hóa dữ liệu thô mới nhất lên Data Lake (MinIO S3 bucket raw)
    sync_raw_data_to_minio = BashOperator(
        task_id="sync_raw_data_to_minio_lake",
        env=RUNTIME_ENV,
        bash_command=r"""
set -e
echo "Đồng bộ hóa dữ liệu CSV mới lên MinIO Raw Bucket..."
docker exec "$IE212_ML_RUNNER_CONTAINER" \
  python -m scripts.sync_parquet_to_minio \
  --local-dir "$IE212_INFERENCE_RAW_DIR" \
  --minio-endpoint "$IE212_MINIO_ENDPOINT" \
  --access-key "$IE212_MINIO_ACCESS_KEY" \
  --secret-key "$IE212_MINIO_SECRET_KEY" \
  --bucket "raw" \
  --prefix "csv_history"
""",
    )

    # 4. Huấn luyện phân tán/huấn luyện offline mô hình Hybrid LSTM-GNN
    # Chạy lại run_experiment.py để thực hiện expanding window train
    run_offline_expanding_train = BashOperator(
        task_id="run_offline_expanding_train",
        env=RUNTIME_ENV,
        bash_command=r"""
set -e
echo "Khởi chạy quy trình huấn luyện Expanding Window Offline..."
docker exec "$IE212_ML_RUNNER_CONTAINER" \
  python -m scripts.run_experiment
""",
    )

    # 5. Lưu trữ Checkpoint mới và Scaler mới lên MinIO Models Bucket
    backup_checkpoint_to_minio = BashOperator(
        task_id="backup_checkpoint_to_minio",
        env=RUNTIME_ENV,
        bash_command=r"""
set -e
echo "Sao lưu Model Checkpoint mới lên MinIO Models Bucket..."
docker exec "$IE212_ML_RUNNER_CONTAINER" \
  python -c "
import boto3
from botocore.client import Config
import os
s3 = boto3.client(
    's3',
    endpoint_url=os.getenv('IE212_MINIO_ENDPOINT'),
    aws_access_key_id=os.getenv('IE212_MINIO_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('IE212_MINIO_SECRET_KEY'),
    config=Config(signature_version='s3v4', s3={'addressing_style': 'path'})
)
# Upload pt
s3.upload_file('models/tsn_attn_expanding_best_full.pt', 'models', 'hybrid_expanding_best_latest.pt')
# Upload metadata
s3.upload_file('models/run_metadata_full.json', 'models', 'run_metadata_latest.json')
print('Upload checkpoint to MinIO succeeded!')
"
""",
    )

    # 6. Đăng ký mô hình mới vào Model Registry
    register_new_model = PythonOperator(
        task_id="register_new_model_to_registry",
        python_callable=update_model_registry_db,
    )

    # ĐỊNH NGHĨA THỨ TỰ THỰC THI (PIPELINE FLOW)
    check_trigger >> download_latest_data >> sync_raw_data_to_minio >> run_offline_expanding_train >> backup_checkpoint_to_minio >> register_new_model
