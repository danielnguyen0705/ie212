# IE212 - Stock Price Prediction with Local ML Pipeline and Big Data Roadmap

## 1. Giới thiệu

Đây là project môn **IE212 - Công nghệ dữ liệu lớn**, tập trung vào bài toán **dự đoán giá cổ phiếu** bằng mô hình lai giữa **LSTM** và **GNN**, sau đó từng bước tích hợp mô hình vào một hệ thống Big Data hoàn chỉnh.

Project hiện được triển khai theo 2 giai đoạn chính:

- **Giai đoạn 1 - Local ML Project**
  - chạy notebook nghiên cứu
  - tách code khỏi notebook thành project Python có cấu trúc
  - chạy experiment ngoài notebook
  - lưu checkpoint model
  - kiểm tra load lại checkpoint
  - chạy inference từ checkpoint
- **Giai đoạn 2 - Big Data System**
  - dựng hạ tầng bằng Docker Compose
  - storage layer:
    - PostgreSQL
    - MinIO
  - streaming layer:
    - Kafka
  - processing layer:
    - Spark standalone
    - Spark batch read từ Kafka
    - Spark structured streaming từ Kafka
    - Spark structured streaming ghi sang PostgreSQL
    - Spark batch ghi Parquet sang MinIO
    - Spark batch ghi PostgreSQL
  - orchestration layer:
    - Airflow
    - DAG smoke test
    - DAG validation pipeline
    - DAG full validation pipeline
    - DAG Spark execution pipeline
    - DAG inference ingest pipeline
    - DAG end-to-end inference pipeline
  - inference layer:
    - build inference bundle từ raw CSV
    - load checkpoint hybrid
    - sinh prediction JSON
    - lưu prediction vào PostgreSQL
    - orchestration toàn bộ bằng Airflow

---

## 2. Trạng thái hiện tại

### Đã hoàn thành

#### Local ML phase

- tạo môi trường `.venv`
- cài dependencies qua `requirements.txt`
- chạy notebook thành công trong VS Code
- tách code từ notebook thành các module trong `src/`
- tạo các script trong `scripts/`
- chạy experiment ngoài notebook thành công
- lưu checkpoint model thành công
- load lại checkpoint thành công
- inspect checkpoint hybrid thành công
- build inference bundle thành công
- chạy inference từ checkpoint thành công
- sinh file `outputs/inference/latest_prediction.json`

#### Big Data phase

- tạo thư mục `compose/`
- dựng thành công các service bằng Docker Compose:
  - `PostgreSQL`
  - `MinIO`
  - `Kafka`
  - `Spark Master`
  - `Spark Worker`
  - `Airflow API Server`
  - `Airflow Scheduler`
  - `Airflow Dag Processor`
  - `Airflow Triggerer`
  - `MinIO Client`
  - `ML Inference Runner`
- PostgreSQL đã có:
  - schema `stock`
  - bảng `stock.predictions`
  - bảng `stock.model_registry`
  - bảng `stock.kafka_ticks`
  - bảng `stock.kafka_ticks_batch`
  - bảng `stock.pipeline_audit`
  - bảng `stock.inference_predictions`
- MinIO đã có bucket:
  - `raw`
  - `processed`
  - `models`
  - `artifacts`
- Kafka đã test thành công:
  - tạo topic `stock-price`
  - producer gửi message
  - consumer đọc lại message
- Spark đã test thành công:
  - `simple_spark_check.py`
  - `read_kafka_batch.py`
  - `read_kafka_stream.py`
  - `write_kafka_stream_to_postgres.py`
  - `write_kafka_batch_to_parquet.py`
  - `write_kafka_batch_to_postgres.py`
- Airflow đã test thành công:
  - login UI thành công
  - `ie212_smoke_test` thành công
  - `ie212_data_pipeline` thành công
  - `ie212_full_validation_pipeline` thành công
  - `ie212_spark_exec_pipeline` thành công
  - `ie212_inference_ingest_pipeline` thành công
  - `ie212_end_to_end_inference_pipeline` thành công
- custom Airflow image có Docker CLI đã build thành công
- custom ML inference runner image đã build thành công với `torch CPU`

---

## 3. Cấu trúc thư mục hiện tại

```text
IE212/
├── .venv/
├── airflow/
│   ├── dags/
│   │   ├── ie212_smoke_test.py
│   │   ├── ie212_data_pipeline.py
│   │   ├── ie212_full_validation_pipeline.py
│   │   ├── ie212_spark_exec_pipeline.py
│   │   ├── ie212_inference_ingest_pipeline.py
│   │   ├── ie212_end_to_end_inference_pipeline.py
│   │   └── ie212_settings.py
│   ├── logs/
│   ├── plugins/
│   └── Dockerfile
├── compose/
│   ├── compose.yaml
│   ├── .env
│   └── postgres/
│       └── init/
│           └── 001_init.sql
├── data/
│   ├── raw/
│   ├── processed/
│   └── inference/
│       └── latest_window.npz
├── models/
│   ├── hybrid_expanding_best_full.pt
│   ├── lstm_expanding_best_full.pt
│   └── run_metadata_full.json
├── notebooks/
├── outputs/
│   └── inference/
│       └── latest_prediction.json
├── scripts/
│   ├── inspect_checkpoint.py
│   ├── run_checkpoint_inference.py
│   ├── build_latest_inference_bundle.py
│   ├── save_inference_to_postgres.py
│   ├── run_experiment.py
│   ├── run_train.py
│   ├── test_expanding_data.py
│   ├── test_graph_builder.py
│   ├── test_load_checkpoint.py
│   ├── test_model_forward.py
│   └── test_prepare_step.py
├── services/
│   ├── spark/
│   │   ├── jobs/
│   │   │   ├── simple_spark_check.py
│   │   │   ├── read_kafka_batch.py
│   │   │   ├── read_kafka_stream.py
│   │   │   ├── write_kafka_stream_to_postgres.py
│   │   │   ├── write_kafka_batch_to_parquet.py
│   │   │   └── write_kafka_batch_to_postgres.py
│   │   └── out/
│   │       └── kafka_ticks_parquet/
│   └── inference/
│       ├── Dockerfile
│       └── requirements.infer.txt
├── src/
├── .gitignore
├── README.md
└── requirements.txt
```

## 4. Ý nghĩa các thư mục chính

- `src/`: mã nguồn chính sau khi tách khỏi notebook
- `scripts/`: các script train, test, evaluate, experiment, inference
- `notebooks/`: notebook nghiên cứu gốc
- `data/raw/`: dữ liệu cổ phiếu theo từng ticker
- `data/inference/`: bundle tensor dùng cho inference
- `outputs/inference/`: file prediction JSON sau khi infer
- `models/`: checkpoint model và metadata
- `compose/`: Docker Compose cho các service Big Data
- `compose/postgres/init/001_init.sql`: SQL khởi tạo schema và bảng ban đầu
- `services/spark/jobs/`: các Spark jobs để test và xử lý dữ liệu
- `services/spark/out/`: output local của Spark trước khi upload MinIO
- `services/inference/`: Dockerfile và requirements cho container ML inference
- `airflow/dags/`: các DAG orchestration
- `airflow/logs/`: log của Airflow
- `airflow/plugins/`: plugin Airflow nếu cần mở rộng
- `airflow/Dockerfile`: custom image Airflow có Docker CLI
- `airflow/dags/ie212_settings.py`: helper đọc cấu hình runtime từ environment variables

## 5. Checkpoint model hiện có

Hiện tại trong thư mục `models/` có 2 checkpoint chính:

- `models/hybrid_expanding_best_full.pt`
- `models/lstm_expanding_best_full.pt`

Checkpoint đang được dùng cho inference pipeline là:

- `models/hybrid_expanding_best_full.pt`

Kết quả inspect checkpoint hybrid:

- `seq_input_dim = 1`
- `node_input_dim = 7`
- `lstm_hidden = 64`
- `gnn_hidden = 32`
- `mlp_hidden = 64`

## 6. Các lệnh local ML đã dùng

Kích hoạt môi trường ảo trên Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Chạy các script local ML:

```bash
python -m scripts.run_train
python -m scripts.test_model_forward
python -m scripts.test_expanding_data
python -m scripts.test_graph_builder
python -m scripts.test_prepare_step
python -m scripts.run_experiment
python -m scripts.test_load_checkpoint
```

Kiểm tra checkpoint:

```bash
python -m scripts.inspect_checkpoint --checkpoint models\hybrid_expanding_best_full.pt
python -m scripts.inspect_checkpoint --checkpoint models\lstm_expanding_best_full.pt
```

## 7. Inference local từ checkpoint

### 7.1 Build inference bundle

Script:

- `scripts/build_latest_inference_bundle.py`

Chức năng:

- đọc dữ liệu từ `data/raw/*.csv`
- intersect ngày giao dịch chung giữa các ticker
- build tensor:
  - `X_seq`
  - `X_node`
  - `A`
  - `last_close`
- lưu bundle ra `data/inference/latest_window.npz`

Lệnh chạy:

```bash
python -m scripts.build_latest_inference_bundle --data-dir data\raw --output data\inference\latest_window.npz
```

### 7.2 Chạy checkpoint inference

Script:

- `scripts/run_checkpoint_inference.py`

Chức năng:

- load checkpoint hybrid
- load bundle `.npz`
- chạy inference
- sinh file `outputs/inference/latest_prediction.json`

Lệnh chạy:

```bash
python -m scripts.run_checkpoint_inference --checkpoint models\hybrid_expanding_best_full.pt --input-npz data\inference\latest_window.npz --output-json outputs\inference\latest_prediction.json --device cpu
```

### 7.3 Lưu prediction JSON vào PostgreSQL

Script:

- `scripts/save_inference_to_postgres.py`

Chức năng:

- tạo bảng `stock.inference_predictions` nếu chưa có
- đọc file JSON prediction
- ghi prediction vào PostgreSQL

Lệnh local tiêu chuẩn:

```bash
python -m scripts.save_inference_to_postgres --input-json outputs\inference\latest_prediction.json --model-name hybrid_expanding_best_full --pg-host 127.0.0.1 --pg-port 5432 --pg-db stock_project --pg-user stock_user --pg-password change_me_postgres
```

## 8. Big Data architecture hiện tại

- **Storage layer**
  - PostgreSQL
  - MinIO
- **Streaming layer**
  - Kafka
- **Processing layer**
  - Spark Master
  - Spark Worker
- **Orchestration layer**
  - Airflow API Server
  - Airflow Scheduler
  - Airflow Dag Processor
  - Airflow Triggerer
- **Inference layer**
  - ML Runner container `ie212-ml-infer`
  - PyTorch CPU
  - bundle builder
  - checkpoint inference
  - prediction JSON writer
  - PostgreSQL prediction sink
- **Sink hiện có**
  - PostgreSQL qua Spark Structured Streaming
  - PostgreSQL qua Spark batch
  - MinIO qua Spark batch + Parquet upload
  - PostgreSQL qua inference pipeline

## 9. Shared runtime config

Hiện tại project đã gom các biến dùng chung vào `compose/.env` để giảm hard-code trong DAG.

PostgreSQL:

```env
POSTGRES_DB=stock_project
POSTGRES_USER=stock_user
POSTGRES_PASSWORD=change_me_postgres
POSTGRES_PORT=5432
```

MinIO:

```env
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=change_me_minio
```

Kafka:

```env
KAFKA_TOPIC_STOCK_PRICE=stock-price
```

Airflow:

```env
AIRFLOW_ADMIN_USER=airflow
AIRFLOW_ADMIN_PASSWORD=airflow
```

IE212 runtime vars:

```env
IE212_POSTGRES_HOST=postgres
IE212_POSTGRES_PORT=5432
IE212_POSTGRES_DB=stock_project
IE212_POSTGRES_USER=stock_user
IE212_POSTGRES_PASSWORD=change_me_postgres

IE212_KAFKA_BOOTSTRAP_SERVERS=kafka:9092
IE212_KAFKA_TOPIC=stock-price

IE212_SPARK_MASTER_CONTAINER=ie212-spark-master
IE212_SPARK_MASTER_URL=spark://spark-master:7077
IE212_SPARK_MASTER_UI_URL=http://spark-master:8080
IE212_SPARK_KAFKA_PACKAGE=org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2
IE212_POSTGRES_JDBC_PACKAGE=org.postgresql:postgresql:42.7.10

IE212_MINIO_CLIENT_CONTAINER=ie212-minio-client
IE212_MINIO_ENDPOINT=http://minio:9000
IE212_MINIO_ACCESS_KEY=minioadmin
IE212_MINIO_SECRET_KEY=change_me_minio
IE212_MINIO_PROCESSED_BUCKET=processed
IE212_MINIO_PARQUET_PREFIX=kafka_ticks_parquet

IE212_PARQUET_LOCAL_DIR=/opt/airflow/shared/spark_out/kafka_ticks_parquet
IE212_SPARK_PARQUET_DIRNAME=kafka_ticks_parquet

IE212_ML_RUNNER_CONTAINER=ie212-ml-infer
IE212_MODEL_CHECKPOINT=/workspace/models/hybrid_expanding_best_full.pt
IE212_MODEL_NAME=hybrid_expanding_best_full
IE212_INFERENCE_RAW_DIR=/workspace/data/raw
IE212_INFERENCE_BUNDLE_PATH=/workspace/data/inference/latest_window.npz
IE212_INFERENCE_OUTPUT_JSON=/workspace/outputs/inference/latest_prediction.json
```

## 10. Cách chạy toàn bộ system

Vào thư mục compose:

```bash
cd compose
```

Khởi động các service chính:

```bash
docker compose up -d
```

Khởi động thêm `minio-client` nếu cần:

```bash
docker compose --profile manual up -d minio-client
```

Build và chạy ML inference runner:

```bash
docker compose up -d --build ml-infer
```

Kiểm tra trạng thái:

```bash
docker compose ps
```

## 11. PostgreSQL

Kiểm tra schema:

```bash
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "\dn"
```

Kiểm tra bảng trong schema stock:

```bash
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "\dt stock.*"
```

Query bảng stream sink:

```bash
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "SELECT id, symbol, price, topic, partition_id, kafka_offset, event_time, ingested_at FROM stock.kafka_ticks ORDER BY id DESC LIMIT 10;"
```

Query bảng batch sink:

```bash
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "SELECT COUNT(*) FROM stock.kafka_ticks_batch;"
```

Query bảng audit pipeline:

```bash
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "SELECT id, run_id, checked_at, kafka_ok, spark_ok, minio_ok, postgres_ok, parquet_local_ok, kafka_ticks_count, parquet_files_count, has_success_marker, missing_tables, notes FROM stock.pipeline_audit ORDER BY id DESC LIMIT 10;"
```

Query bảng prediction inference:

```bash
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "SELECT COUNT(*) FROM stock.inference_predictions;"
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "SELECT prediction_run_id, as_of_date, model_name, ticker, last_close, pred_close, pred_return, graph_gate, created_at FROM stock.inference_predictions ORDER BY id DESC LIMIT 20;"
```

Lưu ý: `compose/postgres/init/001_init.sql` hiện vẫn là phần khởi tạo nền ban đầu. Nếu dựng môi trường mới hoàn toàn, cần bảo đảm các bảng `stock.kafka_ticks`, `stock.kafka_ticks_batch`, `stock.pipeline_audit`, `stock.inference_predictions` đã tồn tại trước khi chạy các job/DAG tương ứng.

## 12. MinIO

Health check:

```bash
curl.exe -i http://localhost:9000/minio/health/live
```

Mở UI:

```text
http://localhost:9001
```

Bucket hiện có:

- `raw`
- `processed`
- `models`
- `artifacts`

Kiểm tra object Parquet: vào bucket `processed` và kiểm tra thư mục chứa output Parquet.

## 13. Kafka

Khởi động Kafka riêng:

```bash
docker compose up -d kafka
```

Xem log:

```bash
docker compose logs kafka --tail=50
```

Tạo topic test:

```bash
docker exec -it ie212-kafka /opt/kafka/bin/kafka-topics.sh --create --topic stock-price --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
```

Liệt kê topic:

```bash
docker exec -it ie212-kafka /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092
```

Producer:

```bash
docker exec -it ie212-kafka /opt/kafka/bin/kafka-console-producer.sh --topic stock-price --bootstrap-server localhost:9092
```

Ví dụ:

```json
{"symbol":"AAPL","price":210.15}
{"symbol":"MSFT","price":438.20}
{"symbol":"AMD","price":167.05}
```

Consumer:

```bash
docker exec -it ie212-kafka /opt/kafka/bin/kafka-console-consumer.sh --topic stock-price --from-beginning --bootstrap-server localhost:9092 --max-messages 3
```

## 14. Spark standalone

Khởi động Spark:

```bash
docker compose up -d spark-master spark-worker
```

Kiểm tra trạng thái:

```bash
docker compose ps
```

UI:

- Spark Master: `http://localhost:8080`
- Spark Worker: `http://localhost:8081`

Smoke test:

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 /opt/spark/jobs/simple_spark_check.py
```

## 15. Các Spark jobs hiện có

Batch read từ Kafka:

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2 /opt/spark/jobs/read_kafka_batch.py
```

Structured Streaming read từ Kafka:

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2 /opt/spark/jobs/read_kafka_stream.py
```

Structured Streaming ghi PostgreSQL:

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2,org.postgresql:postgresql:42.7.10 /opt/spark/jobs/write_kafka_stream_to_postgres.py
```

Batch ghi Parquet:

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2 /opt/spark/jobs/write_kafka_batch_to_parquet.py
```

Batch ghi PostgreSQL:

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2,org.postgresql:postgresql:42.7.10 /opt/spark/jobs/write_kafka_batch_to_postgres.py
```

## 16. ML inference runner

Service:

- `ie212-ml-infer`

Chức năng:

- chạy bundle builder
- chạy checkpoint inference
- chạy script save prediction vào PostgreSQL

Test thư viện trong container:

```bash
docker exec -it ie212-ml-infer python -c "import torch, pandas, numpy, psycopg2; print(torch.__version__)"
```

Kỳ vọng: in ra version kiểu `2.11.0+cpu`.

## 17. Airflow setup

Build custom Airflow image:

```bash
docker build -t ie212-airflow-custom:local ./airflow --progress=plain
```

Kiểm tra Docker CLI trong Airflow:

```bash
docker exec -it ie212-airflow-scheduler sh -lc "docker version"
```

Xem log apiserver:

```bash
docker compose logs airflow-apiserver --tail=200
```

Xem log scheduler:

```bash
docker compose logs airflow-scheduler --tail=200
```

Mở UI:

```text
http://localhost:8088
```

## 18. Các DAG Airflow hiện có

### 18.1 ie212_smoke_test

Chức năng:

- smoke test Airflow stack
- kiểm tra task đơn giản chạy được

### 18.2 ie212_data_pipeline

Chức năng:

- tạo/đảm bảo bảng audit
- kiểm tra Kafka
- kiểm tra Spark Master
- kiểm tra MinIO
- kiểm tra PostgreSQL
- ghi audit vào `stock.pipeline_audit`

### 18.3 ie212_full_validation_pipeline

Chức năng:

- kiểm tra Kafka, Spark, MinIO, PostgreSQL
- kiểm tra local Parquet output
- ghi audit đầy đủ hơn vào `stock.pipeline_audit`

### 18.4 ie212_spark_exec_pipeline

Chức năng:

- gọi Spark batch job ghi PostgreSQL
- kiểm tra bảng `stock.kafka_ticks_batch`
- gọi Spark batch job ghi Parquet
- kiểm tra local Parquet
- upload Parquet lên MinIO
- ghi audit cuối pipeline vào `stock.pipeline_audit`

### 18.5 ie212_inference_ingest_pipeline

Chức năng:

- ingest `outputs/inference/latest_prediction.json`
- lưu prediction vào `stock.inference_predictions`
- validate bảng prediction

### 18.6 ie212_end_to_end_inference_pipeline

Chức năng:

- build `latest_window.npz`
- chạy checkpoint inference
- lưu prediction vào PostgreSQL
- validate kết quả cuối

Đây là DAG end-to-end inference hoàn chỉnh hiện tại.

### 18.7 ie212_settings

Chức năng:

- đọc biến môi trường IE212
- tạo PostgreSQL connection helper
- gom runtime env để dùng lại trong DAG

## 19. Kết quả đã xác nhận thành công

### Storage

- PostgreSQL healthy
- MinIO UI truy cập được
- bucket đã tạo xong

### Streaming

- Kafka healthy
- topic `stock-price` đã tạo
- producer/consumer test thành công

### Processing

- Spark Master/Worker chạy ổn
- smoke test Spark thành công
- stream sink vào PostgreSQL thành công
- batch sink vào PostgreSQL thành công
- batch Parquet output thành công
- upload Parquet vào MinIO thành công

### Inference

- inspect checkpoint hybrid thành công
- build inference bundle thành công
- run checkpoint inference thành công
- prediction JSON sinh thành công
- prediction lưu vào PostgreSQL thành công

### Orchestration

- Airflow stack chạy ổn
- login Airflow thành công
- `ie212_smoke_test` thành công
- `ie212_data_pipeline` thành công
- `ie212_full_validation_pipeline` thành công
- `ie212_spark_exec_pipeline` thành công
- `ie212_inference_ingest_pipeline` thành công
- `ie212_end_to_end_inference_pipeline` thành công

### Database evidence

- `stock.kafka_ticks_batch` có dữ liệu
- `stock.pipeline_audit` có nhiều bản ghi audit hợp lệ
- `stock.inference_predictions` hiện có dữ liệu prediction được lưu nhiều lần
- sau lần chạy `ie212_end_to_end_inference_pipeline`, tổng số dòng prediction đã tăng thêm đúng theo số ticker

## 20. Quick start ngắn gọn

Local ML:

```powershell
.\.venv\Scripts\Activate.ps1
python -m scripts.inspect_checkpoint --checkpoint models\hybrid_expanding_best_full.pt
python -m scripts.build_latest_inference_bundle --data-dir data\raw --output data\inference\latest_window.npz
python -m scripts.run_checkpoint_inference --checkpoint models\hybrid_expanding_best_full.pt --input-npz data\inference\latest_window.npz --output-json outputs\inference\latest_prediction.json --device cpu
```

Big Data services:

```bash
cd compose
docker compose up -d
docker compose --profile manual up -d minio-client
docker compose up -d --build ml-infer
docker compose ps
```

PostgreSQL kiểm tra nhanh:

```bash
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "SELECT COUNT(*) FROM stock.kafka_ticks_batch;"
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "SELECT COUNT(*) FROM stock.inference_predictions;"
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "SELECT prediction_run_id, as_of_date, model_name, ticker, last_close, pred_close, pred_return, graph_gate, created_at FROM stock.inference_predictions ORDER BY id DESC LIMIT 20;"
```

Airflow kiểm tra nhanh:

```bash
docker exec -it ie212-airflow-scheduler sh -lc "docker version"
docker compose logs airflow-apiserver --tail=200
docker compose logs airflow-scheduler --tail=200
```

UI:

```text
MinIO: http://localhost:9001
Spark Master: http://localhost:8080
Spark Worker: http://localhost:8081
Airflow: http://localhost:8088
```

## 21. Ghi chú

- Hard-code secrets trong DAG đã được giảm đáng kể nhờ `.env` và `ie212_settings.py`.
- `torch` trong `ml-infer` đang dùng bản CPU để tránh kéo CUDA package quá nặng.
- Pipeline inference hiện dựa trên dữ liệu raw CSV cục bộ, chưa lấy trực tiếp từ Kafka/Spark output.
- Đây là checkpoint rất tốt trước khi dựng API demo.

## 22. Bước tiếp theo

Roadmap tiếp theo hợp lý:

- dựng FastAPI để expose prediction mới nhất
- tạo endpoint đọc prediction từ PostgreSQL
- chuẩn bị lớp demo cho đồ án
- cân nhắc nối inference input với processed data thay vì raw CSV cục bộ
- làm dashboard hoặc UI đơn giản để trình diễn

## 23. Mục đích project

Project phục vụ:

- tái hiện và cải tiến bài toán dự đoán giá cổ phiếu bằng mô hình hybrid temporal-relational
- triển khai pipeline Big Data end-to-end cho đồ án môn IE212
- chứng minh được cả:
  - data pipeline
  - model checkpoint pipeline
  - inference pipeline
  - orchestration pipeline
- làm nền tảng để tích hợp FastAPI và demo hệ thống hoàn chỉnh
