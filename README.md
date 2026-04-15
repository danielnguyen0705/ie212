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
  - orchestration layer:
    - Airflow
    - DAG smoke test
    - DAG validation pipeline
    - DAG execution pipeline
  - các bước tiếp theo sẽ là:
    - làm sạch và chuẩn hóa DAG execution
    - tích hợp model local vào pipeline
    - FastAPI
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
- dựng thành công các service đầu tiên bằng Docker Compose:
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
- PostgreSQL đã được khởi tạo:
  - schema `stock`
  - bảng `stock.predictions`
  - bảng `stock.model_registry`
  - bảng `stock.kafka_ticks`
  - bảng `stock.kafka_ticks_batch`
  - bảng `stock.pipeline_audit`
- MinIO đã được khởi tạo bucket:
  - `raw`
  - `processed`
  - `models`
  - `artifacts`
- Kafka đã được kiểm tra thành công:
  - tạo topic `stock-price`
  - producer gửi message vào topic
  - consumer đọc lại message từ topic
- Spark đã được kiểm tra thành công:
  - chạy Spark standalone smoke test
  - submit job `simple_spark_check.py`
  - đọc batch từ Kafka bằng `read_kafka_batch.py`
  - đọc stream từ Kafka bằng `read_kafka_stream.py`
  - ghi stream từ Kafka sang PostgreSQL bằng `write_kafka_stream_to_postgres.py`
  - ghi batch từ Kafka ra Parquet bằng `write_kafka_batch_to_parquet.py`
  - ghi batch từ Kafka sang PostgreSQL bằng `write_kafka_batch_to_postgres.py`
  - upload Parquet lên MinIO bucket `processed`
- Airflow đã được kiểm tra thành công:
  - login vào UI thành công
  - DAG `ie212_smoke_test` chạy thành công
  - DAG `ie212_data_pipeline` chạy thành công
  - DAG `ie212_full_validation_pipeline` chạy thành công
  - DAG `ie212_spark_exec_pipeline` chạy thành công
  - ghi audit thành công vào bảng `stock.pipeline_audit`

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
│   │   └── ie212_spark_exec_pipeline.py
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
- `scripts/`: các script test, train, evaluate, experiment
- `notebooks/`: notebook nghiên cứu gốc
- `data/`: dữ liệu raw và processed
- `outputs/`: kết quả thực nghiệm
- `models/`: checkpoint model và metadata
- `compose/`: Docker Compose cho các service Big Data
- `compose/postgres/init/001_init.sql`: SQL khởi tạo schema và bảng ban đầu
- `services/spark/jobs/`: các job Spark dùng để smoke test, đọc batch, đọc stream và ghi dữ liệu ra sink
- `services/spark/out/`: dữ liệu output từ Spark trước khi upload lên MinIO
- `airflow/dags/`: các DAG dùng để smoke test, validation và orchestration pipeline
- `airflow/logs/`: log của Airflow
- `airflow/plugins/`: plugin mở rộng cho Airflow nếu cần về sau
- `airflow/Dockerfile`: custom image Airflow có Docker CLI để gọi `docker exec` và `docker run`

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
- `test_model_forward`: kiểm tra forward pass của model
- `test_expanding_data`: kiểm tra chuẩn bị dữ liệu theo expanding window
- `test_graph_builder`: kiểm tra graph construction
- `test_prepare_step`: kiểm tra train/val/test pack cho từng expanding step
- `run_experiment`: chạy thực nghiệm ngoài notebook
- `test_load_checkpoint`: kiểm tra load lại checkpoint đã lưu

## 6. Big Data phase - Storage, Streaming, Processing, Orchestration

Hiện tại project đã dựng thành công các service Big Data đầu tiên bằng Docker Compose:

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
- **Sink đã có**
  - PostgreSQL qua Spark Structured Streaming
  - MinIO qua Spark batch + Parquet upload
- **Execution pipeline đã có**
  - Spark batch ghi PostgreSQL
  - kiểm tra bảng batch
  - Spark batch ghi Parquet
  - kiểm tra Parquet local
  - upload MinIO
  - ghi audit cuối pipeline

## 7. Cấu hình Docker Compose hiện tại

Các file liên quan:

- `compose/compose.yaml`
- `compose/.env`
- `compose/postgres/init/001_init.sql`

Service đang có:

- `ie212-postgres`
- `ie212-minio`
- `ie212-minio-client`
- `ie212-kafka`
- `ie212-spark-master`
- `ie212-spark-worker`
- `ie212-airflow-apiserver`
- `ie212-airflow-scheduler`
- `ie212-airflow-dag-processor`
- `ie212-airflow-triggerer`

Bucket MinIO đã có:

- `raw`
- `processed`
- `models`
- `artifacts`

Topic Kafka đã test:

- `stock-price`

## 8. Cách chạy các service hiện tại

1. Đi vào thư mục compose:

```bash
cd compose
```

2. Khởi động toàn bộ container hiện tại:

```bash
docker compose up -d
```

3. Nếu cần chạy thêm `minio-client` profile:

```bash
docker compose --profile manual up -d minio-client
```

4. Kiểm tra trạng thái container:

```bash
docker compose ps
```

## 9. Các lệnh kiểm tra PostgreSQL

Kiểm tra schema:

```bash
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "\dn"
```

Kiểm tra bảng trong schema `stock`:

```bash
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "\dt stock.*"
```

Query dữ liệu Kafka đã được Spark ghi vào PostgreSQL:

```bash
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "SELECT id, symbol, price, topic, partition_id, kafka_offset, event_time, ingested_at FROM stock.kafka_ticks ORDER BY id DESC LIMIT 10;"
```

Query bảng batch do Spark batch job ghi:

```bash
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "SELECT COUNT(*) FROM stock.kafka_ticks_batch;"
```

Query bảng audit pipeline:

```bash
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "SELECT id, run_id, checked_at, kafka_ok, spark_ok, minio_ok, postgres_ok, parquet_local_ok, kafka_ticks_count, parquet_files_count, has_success_marker, missing_tables, notes FROM stock.pipeline_audit ORDER BY id DESC LIMIT 10;"
```

Kết quả mong đợi:

- schema `stock`
- bảng `stock.predictions`
- bảng `stock.model_registry`
- bảng `stock.kafka_ticks`
- bảng `stock.kafka_ticks_batch`
- bảng `stock.pipeline_audit`
- dữ liệu mới do Spark ghi từ Kafka xuất hiện trong `stock.kafka_ticks`
- dữ liệu batch do DAG execution ghi xuất hiện trong `stock.kafka_ticks_batch`
- dữ liệu audit từ Airflow xuất hiện trong `stock.pipeline_audit`

Lưu ý: `compose/postgres/init/001_init.sql` hiện vẫn mô tả phần khởi tạo bảng nền ban đầu. Nếu dựng môi trường hoàn toàn mới, hãy bảo đảm các bảng `stock.kafka_ticks`, `stock.kafka_ticks_batch`, `stock.pipeline_audit` đã được tạo trước khi chạy các job/DAG liên quan.

## 10. Các lệnh kiểm tra MinIO

Health check:

```bash
curl.exe -i http://localhost:9000/minio/health/live
```

Mở giao diện web:

```text
http://localhost:9001
```

Thông tin đăng nhập xem trong file `compose/.env`.

Nên đổi password mặc định trước khi dùng lâu dài.

Kiểm tra object đã upload:

- mở bucket `processed`
- kiểm tra thư mục chứa Parquet output

## 11. Các lệnh kiểm tra Kafka

Khởi động Kafka riêng:

```bash
docker compose up -d kafka
```

Kiểm tra log Kafka:

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

Gửi message bằng producer:

```bash
docker exec -it ie212-kafka /opt/kafka/bin/kafka-console-producer.sh --topic stock-price --bootstrap-server localhost:9092
```

Ví dụ message:

```json
{"symbol":"AAPL","price":210.15}
{"symbol":"MSFT","price":438.20}
{"symbol":"AMD","price":167.05}
```

Đọc message bằng consumer:

```bash
docker exec -it ie212-kafka /opt/kafka/bin/kafka-console-consumer.sh --topic stock-price --from-beginning --bootstrap-server localhost:9092 --max-messages 3
```

Kết quả mong đợi: consumer đọc lại đúng message đã gửi vào topic `stock-price`.

## 12. Các lệnh kiểm tra Spark standalone

Khởi động Spark:

```bash
docker compose up -d spark-master spark-worker
```

Kiểm tra trạng thái:

```bash
docker compose ps
```

Spark Master UI: `http://localhost:8080`

Spark Worker UI: `http://localhost:8081`

Chạy smoke test Spark:

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 /opt/spark/jobs/simple_spark_check.py
```

Kết quả mong đợi:

- Spark Master và Spark Worker chạy ổn
- Worker đăng ký thành công với Master
- Job `ie212-spark-check` chạy thành công
- DataFrame hiển thị 3 dòng dữ liệu mẫu
- Row count = 3

## 13. Spark batch read từ Kafka

File job: `services/spark/jobs/read_kafka_batch.py`

Chạy batch job:

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2 /opt/spark/jobs/read_kafka_batch.py
```

## 14. Spark Structured Streaming từ Kafka

File job: `services/spark/jobs/read_kafka_stream.py`

Chạy stream job:

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2 /opt/spark/jobs/read_kafka_stream.py
```

## 15. Spark Structured Streaming ghi sang PostgreSQL

File job: `services/spark/jobs/write_kafka_stream_to_postgres.py`

Chạy stream job ghi PostgreSQL:

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2,org.postgresql:postgresql:42.7.10 /opt/spark/jobs/write_kafka_stream_to_postgres.py
```

## 16. Spark batch ghi Parquet và upload sang MinIO

File job: `services/spark/jobs/write_kafka_batch_to_parquet.py`

Chạy batch job ghi Parquet:

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2 /opt/spark/jobs/write_kafka_batch_to_parquet.py
```

Kiểm tra file Parquet trên host:

```powershell
Get-ChildItem services\spark\out\kafka_ticks_parquet -Recurse
```

Upload Parquet lên MinIO bằng minio-client:

```bash
docker exec -it ie212-minio-client sh -lc "mc alias set local http://minio:9000 minioadmin change_me_minio && mc cp --recursive /upload/kafka_ticks_parquet local/processed/kafka_ticks_parquet"
```

Kiểm tra object trên MinIO qua UI `http://localhost:9001` hoặc bằng lệnh `mc ls` bên trong `ie212-minio-client`.

## 17. Spark batch ghi PostgreSQL

File job: `services/spark/jobs/write_kafka_batch_to_postgres.py`

Chạy batch job ghi PostgreSQL:

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2,org.postgresql:postgresql:42.7.10 /opt/spark/jobs/write_kafka_batch_to_postgres.py
```

Kết quả mong đợi:

- bảng `stock.kafka_ticks_batch` được tạo hoặc ghi lại
- query `SELECT COUNT(*) FROM stock.kafka_ticks_batch;` trả về số dòng lớn hơn 0

## 18. Airflow setup và kiểm tra

Tạo thư mục Airflow:

```powershell
New-Item -ItemType Directory -Path airflow\dags -Force
New-Item -ItemType Directory -Path airflow\logs -Force
New-Item -ItemType Directory -Path airflow\plugins -Force
```

Build custom Airflow image có Docker CLI:

```bash
docker build -t ie212-airflow-custom:local ./airflow --progress=plain
```

Service Airflow hiện có:

- `ie212-airflow-apiserver`
- `ie212-airflow-scheduler`
- `ie212-airflow-dag-processor`
- `ie212-airflow-triggerer`

Kiểm tra trạng thái:

```bash
docker compose ps
```

Kiểm tra Docker CLI bên trong Airflow:

```bash
docker exec -it ie212-airflow-scheduler sh -lc "docker version"
```

Xem log apiserver để lấy password simple auth:

```bash
docker compose logs airflow-apiserver --tail=200
```

Mở UI Airflow: `http://localhost:8088`

## 19. Các DAG Airflow hiện có

### DAG smoke test

File: `airflow/dags/ie212_smoke_test.py`

Chức năng:

- kiểm tra Airflow stack chạy được
- 2 task `hello` và `summary` chạy thành công

### DAG pipeline validation cơ bản

File: `airflow/dags/ie212_data_pipeline.py`

Chức năng:

- đảm bảo bảng `stock.pipeline_audit` tồn tại
- kiểm tra Kafka
- kiểm tra Spark Master
- kiểm tra MinIO
- kiểm tra PostgreSQL
- ghi audit row vào `stock.pipeline_audit`
- xác nhận pipeline cơ bản đang sống

### DAG full validation pipeline

File: `airflow/dags/ie212_full_validation_pipeline.py`

Chức năng:

- kiểm tra Kafka, Spark, MinIO, PostgreSQL
- kiểm tra local Parquet output
- ghi audit row đầy đủ hơn vào `stock.pipeline_audit`

### DAG execution pipeline

File: `airflow/dags/ie212_spark_exec_pipeline.py`

Chức năng:

- gọi Spark batch job ghi PostgreSQL
- kiểm tra bảng `stock.kafka_ticks_batch`
- gọi Spark batch job ghi Parquet
- kiểm tra local Parquet output
- upload Parquet lên MinIO
- ghi audit cuối pipeline vào `stock.pipeline_audit`

Kiểm tra audit do Airflow ghi:

```bash
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "SELECT id, run_id, checked_at, kafka_ok, spark_ok, minio_ok, postgres_ok, parquet_local_ok, kafka_ticks_count, parquet_files_count, has_success_marker, missing_tables, notes FROM stock.pipeline_audit ORDER BY id DESC LIMIT 10;"
```

## 20. Các lệnh quản lý Docker Compose

```bash
docker compose ps
docker compose ps -a
docker compose logs postgres
docker compose logs minio
docker compose logs kafka
docker compose logs spark-master
docker compose logs spark-worker
docker compose logs airflow-apiserver
docker compose logs airflow-scheduler
docker compose down
docker compose down -v
```

`Cẩn thận:` `down -v` sẽ xóa dữ liệu PostgreSQL, MinIO và các volume liên quan.

## 21. Những gì đã xác nhận thành công

### Local ML

- notebook chạy được
- code sau khi tách vẫn chạy ổn
- experiment chạy ngoài notebook thành công
- checkpoint model đã lưu thành công
- checkpoint đã load lại thành công

### Big Data - Storage

- PostgreSQL container chạy healthy
- schema stock đã được tạo
- bảng `predictions`, `model_registry`, `kafka_ticks`, `kafka_ticks_batch`, `pipeline_audit` đã được tạo
- MinIO web UI truy cập được
- bucket `raw`, `processed`, `models`, `artifacts` đã được tạo

### Big Data - Streaming

- Kafka container chạy healthy
- topic `stock-price` đã được tạo
- producer gửi được message
- consumer đọc lại được message
- smoke test Kafka thành công

### Big Data - Processing

- Spark Master và Spark Worker chạy ổn
- Spark standalone smoke test thành công
- Spark batch đọc Kafka thành công
- Spark structured streaming đọc Kafka thành công
- Spark structured streaming ghi PostgreSQL thành công
- Spark batch ghi Parquet thành công
- Parquet upload lên MinIO thành công
- Spark batch ghi PostgreSQL thành công
- Kafka -> Spark -> PostgreSQL pipeline cơ bản đã hoạt động
- Kafka -> Spark -> MinIO pipeline cơ bản đã hoạt động

### Big Data - Orchestration

- Airflow API Server, Scheduler, Dag Processor, Triggerer chạy ổn
- Airflow UI login thành công
- DAG `ie212_smoke_test` chạy thành công
- DAG `ie212_data_pipeline` chạy thành công
- DAG `ie212_full_validation_pipeline` chạy thành công
- DAG `ie212_spark_exec_pipeline` chạy thành công
- Airflow ghi audit vào `stock.pipeline_audit` thành công

## 22. Bước tiếp theo

Roadmap tiếp theo của project là:

- làm sạch đường dẫn upload MinIO để tránh lồng thư mục trùng tên
- chuẩn hóa DAG execution để dùng biến môi trường thay vì hard-code password
- tích hợp checkpoint model local vào pipeline
- dựng FastAPI để serving model
- xây pipeline end-to-end hoàn chỉnh cho đồ án IE212

## 23. Ghi chú

- local ML phase hiện đã hoàn thành ở mức đủ tốt để chuyển sang hạ tầng
- Big Data phase hiện đã hoàn thành:
  - storage layer
  - streaming layer
  - processing layer
  - sink vào PostgreSQL
  - sink vào MinIO
  - orchestration cơ bản bằng Airflow
  - execution pipeline bằng Airflow
- đây là checkpoint rất tốt trước khi sang model serving và end-to-end pipeline

## 24. Quick start ngắn gọn

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

Kiểm tra PostgreSQL:

```bash
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "\dn"
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "\dt stock.*"
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "SELECT COUNT(*) FROM stock.kafka_ticks_batch;"
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "SELECT id, run_id, checked_at, kafka_ok, spark_ok, minio_ok, postgres_ok, parquet_local_ok, kafka_ticks_count, parquet_files_count, has_success_marker, missing_tables, notes FROM stock.pipeline_audit ORDER BY id DESC LIMIT 10;"
```

Kiểm tra Kafka:

```bash
docker exec -it ie212-kafka /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092
docker exec -it ie212-kafka /opt/kafka/bin/kafka-console-consumer.sh --topic stock-price --from-beginning --bootstrap-server localhost:9092 --max-messages 3
```

Kiểm tra Spark batch ghi PostgreSQL:

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2,org.postgresql:postgresql:42.7.10 /opt/spark/jobs/write_kafka_batch_to_postgres.py
```

Kiểm tra Spark batch ghi Parquet:

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2 /opt/spark/jobs/write_kafka_batch_to_parquet.py
docker exec -it ie212-minio-client sh -lc "mc alias set local http://minio:9000 minioadmin change_me_minio && mc cp --recursive /upload/kafka_ticks_parquet local/processed/kafka_ticks_parquet"
```

Kiểm tra Airflow:

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

## 25. Mục đích project

Project phục vụ:

- tái hiện và cải tiến bài toán dự đoán giá cổ phiếu bằng mô hình hybrid temporal-relational
- triển khai pipeline Big Data end-to-end cho đồ án môn IE212
- làm nền tảng để tích hợp Spark, Kafka, Airflow, FastAPI và model serving trong các bước tiếp theo
