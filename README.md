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
    - DAG execution pipeline
  - config cleanup:
    - gom biến dùng chung vào `.env`
    - truyền biến vào Airflow services qua `compose.yaml`
    - tạo helper `ie212_settings.py` để DAG đọc config runtime
  - các bước tiếp theo:
    - chuẩn hóa output path trên MinIO
    - nối checkpoint model local vào pipeline
    - dựng FastAPI
    - model serving end-to-end

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
- PostgreSQL đã có:
  - schema `stock`
  - bảng `stock.predictions`
  - bảng `stock.model_registry`
  - bảng `stock.kafka_ticks`
  - bảng `stock.kafka_ticks_batch`
  - bảng `stock.pipeline_audit`
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
- custom Airflow image có Docker CLI đã build thành công
- DAG execution hiện đã chạy được chuỗi:
  - Spark batch ghi PostgreSQL
  - kiểm tra batch table
  - Spark batch ghi Parquet
  - kiểm tra local Parquet
  - upload Parquet lên MinIO
  - ghi audit vào PostgreSQL

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
├── services/
│   └── spark/
│       ├── jobs/
│       │   ├── simple_spark_check.py
│       │   ├── read_kafka_batch.py
│       │   ├── read_kafka_stream.py
│       │   ├── write_kafka_stream_to_postgres.py
│       │   ├── write_kafka_batch_to_parquet.py
│       │   └── write_kafka_batch_to_postgres.py
│       └── out/
│           └── kafka_ticks_parquet/
├── data/
├── models/
├── notebooks/
├── outputs/
├── scripts/
├── src/
├── .gitignore
├── README.md
└── requirements.txt
```

## 4. Ý nghĩa các thư mục chính

- `src/`: mã nguồn chính sau khi tách khỏi notebook
- `scripts/`: các script train, test, evaluate, experiment
- `notebooks/`: notebook nghiên cứu gốc
- `data/`: dữ liệu raw và processed
- `outputs/`: kết quả thực nghiệm
- `models/`: checkpoint model và metadata
- `compose/`: Docker Compose cho các service Big Data
- `compose/postgres/init/001_init.sql`: SQL khởi tạo schema và bảng ban đầu
- `services/spark/jobs/`: các Spark jobs để test và xử lý dữ liệu
- `services/spark/out/`: output local của Spark trước khi upload MinIO
- `airflow/dags/`: các DAG orchestration
- `airflow/logs/`: log của Airflow
- `airflow/plugins/`: plugin Airflow nếu cần mở rộng
- `airflow/Dockerfile`: custom image Airflow có Docker CLI
- `airflow/dags/ie212_settings.py`: helper đọc cấu hình runtime từ environment variables

## 5. Các lệnh local ML đã dùng

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

Ý nghĩa nhanh:

- `run_train`: chạy pipeline train cơ bản
- `test_model_forward`: kiểm tra forward pass
- `test_expanding_data`: kiểm tra dữ liệu expanding window
- `test_graph_builder`: kiểm tra graph construction
- `test_prepare_step`: kiểm tra train/val/test pack
- `run_experiment`: chạy thực nghiệm ngoài notebook
- `test_load_checkpoint`: kiểm tra load checkpoint

## 6. Big Data architecture hiện tại

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
- **Sink hiện có**
  - PostgreSQL qua Spark Structured Streaming
  - PostgreSQL qua Spark batch
  - MinIO qua Spark batch + Parquet upload

## 7. Shared runtime config

Hiện tại project đã gom các biến dùng chung vào `compose/.env` để giảm hard-code trong DAG.

Các biến IE212 dùng chung:

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
```

Ý nghĩa:

- DAG không còn hard-code password/container name nhiều như trước
- Airflow services đọc các biến này từ `compose.yaml`
- `ie212_settings.py` dùng để lấy config runtime và tạo PostgreSQL connection

## 8. Cách chạy toàn bộ system

Vào thư mục compose:

```bash
cd compose
```

Khởi động các service chính:

```bash
docker compose up -d
```

Khởi động thêm minio-client profile nếu cần:

```bash
docker compose --profile manual up -d minio-client
```

Kiểm tra trạng thái:

```bash
docker compose ps
```

## 9. PostgreSQL

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

Query bảng audit:

```bash
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "SELECT id, run_id, checked_at, kafka_ok, spark_ok, minio_ok, postgres_ok, parquet_local_ok, kafka_ticks_count, parquet_files_count, has_success_marker, missing_tables, notes FROM stock.pipeline_audit ORDER BY id DESC LIMIT 10;"
```

Kết quả mong đợi:

- có schema `stock`
- có các bảng:
  - `predictions`
  - `model_registry`
  - `kafka_ticks`
  - `kafka_ticks_batch`
  - `pipeline_audit`

Lưu ý: `compose/postgres/init/001_init.sql` hiện vẫn là bản khởi tạo nền. Nếu dựng môi trường mới hoàn toàn, cần đảm bảo các bảng `stock.kafka_ticks`, `stock.kafka_ticks_batch`, `stock.pipeline_audit` được tạo trước khi chạy các job/DAG phụ thuộc.

## 10. MinIO

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

## 11. Kafka

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

## 12. Spark standalone

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

## 13. Các Spark jobs hiện có

### 13.1 Batch read từ Kafka

File: `services/spark/jobs/read_kafka_batch.py`

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2 /opt/spark/jobs/read_kafka_batch.py
```

### 13.2 Structured Streaming read từ Kafka

File: `services/spark/jobs/read_kafka_stream.py`

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2 /opt/spark/jobs/read_kafka_stream.py
```

### 13.3 Structured Streaming ghi PostgreSQL

File: `services/spark/jobs/write_kafka_stream_to_postgres.py`

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2,org.postgresql:postgresql:42.7.10 /opt/spark/jobs/write_kafka_stream_to_postgres.py
```

### 13.4 Batch ghi Parquet

File: `services/spark/jobs/write_kafka_batch_to_parquet.py`

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2 /opt/spark/jobs/write_kafka_batch_to_parquet.py
```

### 13.5 Batch ghi PostgreSQL

File: `services/spark/jobs/write_kafka_batch_to_postgres.py`

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2,org.postgresql:postgresql:42.7.10 /opt/spark/jobs/write_kafka_batch_to_postgres.py
```

## 14. MinIO client

Chạy service minio-client:

```bash
docker compose --profile manual up -d minio-client
```

Upload Parquet thủ công:

```bash
docker exec -it ie212-minio-client sh -lc "mc alias set local http://minio:9000 minioadmin change_me_minio && mc cp --recursive /upload/kafka_ticks_parquet local/processed/kafka_ticks_parquet"
```

## 15. Airflow setup

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

## 16. Các DAG Airflow hiện có

### 16.1 ie212_smoke_test

File: `airflow/dags/ie212_smoke_test.py`

Chức năng:

- smoke test Airflow stack
- kiểm tra task đơn giản chạy được

### 16.2 ie212_data_pipeline

File: `airflow/dags/ie212_data_pipeline.py`

Chức năng:

- tạo/đảm bảo bảng audit
- kiểm tra Kafka
- kiểm tra Spark Master
- kiểm tra MinIO
- kiểm tra PostgreSQL
- ghi audit vào `stock.pipeline_audit`

### 16.3 ie212_full_validation_pipeline

File: `airflow/dags/ie212_full_validation_pipeline.py`

Chức năng:

- kiểm tra Kafka, Spark, MinIO, PostgreSQL
- kiểm tra local Parquet output
- ghi audit đầy đủ hơn vào `stock.pipeline_audit`

### 16.4 ie212_spark_exec_pipeline

File: `airflow/dags/ie212_spark_exec_pipeline.py`

Chức năng:

- gọi Spark batch job ghi PostgreSQL
- kiểm tra bảng `stock.kafka_ticks_batch`
- gọi Spark batch job ghi Parquet
- kiểm tra local Parquet
- upload Parquet lên MinIO
- ghi audit cuối pipeline vào `stock.pipeline_audit`

### 16.5 ie212_settings

File: `airflow/dags/ie212_settings.py`

Chức năng:

- đọc biến môi trường IE212
- tạo PostgreSQL connection helper
- gom runtime env để dùng lại trong DAG

## 17. Kết quả đã xác nhận thành công

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

### Orchestration

- Airflow stack chạy ổn
- login Airflow thành công
- `ie212_smoke_test` thành công
- `ie212_data_pipeline` thành công
- `ie212_full_validation_pipeline` thành công
- `ie212_spark_exec_pipeline` thành công

### Audit / DB evidence

- `stock.kafka_ticks_batch` hiện có dữ liệu
- `stock.pipeline_audit` đã có bản ghi mới nhất với:
  - `kafka_ok = true`
  - `spark_ok = true`
  - `minio_ok = true`
  - `postgres_ok = true`
  - `parquet_local_ok = true`
  - `parquet_files_count > 0`
  - `has_success_marker = true`

## 18. Quick start ngắn gọn

Local ML:

```powershell
.\.venv\Scripts\Activate.ps1
python -m scripts.run_experiment
python -m scripts.test_load_checkpoint
```

Big Data services:

```bash
cd compose
docker compose up -d
docker compose --profile manual up -d minio-client
docker compose ps
```

PostgreSQL kiểm tra nhanh:

```bash
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "SELECT COUNT(*) FROM stock.kafka_ticks_batch;"
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "SELECT id, run_id, checked_at, kafka_ok, spark_ok, minio_ok, postgres_ok, parquet_local_ok, kafka_ticks_count, parquet_files_count, has_success_marker, missing_tables, notes FROM stock.pipeline_audit ORDER BY id DESC LIMIT 10;"
```

Airflow kiểm tra nhanh:

```bash
docker exec -it ie212-airflow-scheduler sh -lc "docker version"
docker compose logs airflow-apiserver --tail=200
docker compose logs airflow-scheduler --tail=200
```

## 19. Ghi chú

- Hiện tại pipeline execution đã chạy thành công.
- Hard-code secrets trong DAG đã được giảm đáng kể nhờ chuyển qua `.env` và `ie212_settings.py`.
- Đường dẫn object trên MinIO vẫn có thể được làm gọn hơn ở bước tiếp theo để tránh lồng thư mục trùng tên.
- Đây là checkpoint rất tốt trước khi tích hợp checkpoint model local và dựng FastAPI.

## 20. Bước tiếp theo

Roadmap tiếp theo:

- làm sạch đường dẫn upload MinIO
- chuẩn bị script inference chuẩn từ checkpoint model local
- cho Airflow gọi inference step
- dựng FastAPI để serving model
- hoàn thiện pipeline end-to-end cho đồ án IE212

## 21. Mục đích project

Project phục vụ:

- tái hiện và cải tiến bài toán dự đoán giá cổ phiếu bằng mô hình hybrid temporal-relational
- triển khai pipeline Big Data end-to-end cho đồ án môn IE212
- làm nền tảng để tích hợp Spark, Kafka, Airflow, FastAPI và model serving trong các bước tiếp theo
