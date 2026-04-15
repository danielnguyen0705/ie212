# IE212 - Stock Price Prediction with Local ML Pipeline and Big Data Roadmap

## 1. Giới thiệu

Đây là project môn `IE212 - Công nghệ dữ liệu lớn`, tập trung vào bài toán dự đoán giá cổ phiếu bằng mô hình lai giữa `LSTM` và `GNN`, sau đó từng bước tích hợp mô hình vào một hệ thống Big Data hoàn chỉnh.

Project hiện được triển khai theo 2 giai đoạn chính:

### Giai đoạn 1 - Local ML Project

- chạy notebook nghiên cứu
- tách code khỏi notebook thành project Python có cấu trúc
- chạy experiment ngoài notebook
- lưu checkpoint model
- kiểm tra load lại checkpoint

### Giai đoạn 2 - Big Data System

- dựng hạ tầng bằng Docker Compose
- storage layer:
- `PostgreSQL`
- `MinIO`
- streaming layer:
- `Kafka`
- processing layer:
- `Spark standalone`
- `Spark batch read từ Kafka`
- `Spark structured streaming từ Kafka`
- `Spark structured streaming ghi sang PostgreSQL`
- `Spark batch ghi Parquet sang MinIO`
- orchestration layer:
- `Airflow`
- `DAG smoke test`
- `DAG thật kiểm tra pipeline`
- các bước tiếp theo sẽ là:
- DAG orchestration mạnh hơn cho Spark jobs
- `FastAPI`
- tích hợp model local vào pipeline Big Data end-to-end

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
- PostgreSQL đã được khởi tạo:
- schema `stock`
- bảng `stock.predictions`
- bảng `stock.model_registry`
- bảng `stock.kafka_ticks`
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
- upload Parquet lên MinIO bucket `processed`
- Airflow đã được kiểm tra thành công:
- login vào UI thành công
- DAG `ie212_smoke_test` chạy thành công
- DAG `ie212_data_pipeline` chạy thành công
- ghi audit thành công vào bảng `stock.pipeline_audit`

## 3. Cấu trúc thư mục hiện tại

```text
IE212/
├── .venv/
├── airflow/
│   ├── dags/
│   │   ├── ie212_smoke_test.py
│   │   └── ie212_data_pipeline.py
│   ├── logs/
│   └── plugins/
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
│       │   └── write_kafka_batch_to_parquet.py
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
- `airflow/dags/`: các DAG dùng để smoke test và orchestration pipeline
- `airflow/logs/`: log của Airflow
- `airflow/plugins/`: plugin mở rộng cho Airflow nếu cần về sau

## 5. Các lệnh local ML đã dùng

### Kích hoạt môi trường ảo trên Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

### Chạy các script local ML

```bash
python -m scripts.run_train
python -m scripts.test_model_forward
python -m scripts.test_expanding_data
python -m scripts.test_graph_builder
python -m scripts.test_prepare_step
python -m scripts.run_experiment
python -m scripts.test_load_checkpoint
```

### Ý nghĩa nhanh

- `run_train`: chạy pipeline train cơ bản
- `test_model_forward`: kiểm tra forward pass của model
- `test_expanding_data`: kiểm tra chuẩn bị dữ liệu theo expanding window
- `test_graph_builder`: kiểm tra graph construction
- `test_prepare_step`: kiểm tra train/val/test pack cho từng expanding step
- `run_experiment`: chạy thực nghiệm ngoài notebook
- `test_load_checkpoint`: kiểm tra load lại checkpoint đã lưu

## 6. Big Data phase - Storage, Streaming, Processing, Orchestration

Hiện tại project đã dựng thành công các service Big Data đầu tiên bằng Docker Compose.

### Storage layer

- `PostgreSQL`
- `MinIO`

### Streaming layer

- `Kafka`

### Processing layer

- `Spark Master`
- `Spark Worker`

### Orchestration layer

- `Airflow API Server`
- `Airflow Scheduler`
- `Airflow Dag Processor`
- `Airflow Triggerer`

### Sink đã có

- `PostgreSQL` qua Spark Structured Streaming
- `MinIO` qua Spark batch + Parquet upload

## 7. Cấu hình Docker Compose hiện tại

Các file liên quan:

- `compose/compose.yaml`
- `compose/.env`
- `compose/postgres/init/001_init.sql`

### Service đang có

- `ie212-postgres`
- `ie212-minio`
- `ie212-kafka`
- `ie212-spark-master`
- `ie212-spark-worker`
- `ie212-airflow-apiserver`
- `ie212-airflow-scheduler`
- `ie212-airflow-dag-processor`
- `ie212-airflow-triggerer`

### Service hỗ trợ

- `minio-client` dùng để upload file từ host mount lên MinIO
- `airflow-init` dùng để migrate metadata database cho Airflow

### Bucket MinIO đã có

- `raw`
- `processed`
- `models`
- `artifacts`

### Topic Kafka đã test

- `stock-price`

## 8. Cách chạy các service hiện tại

### Bước 1: đi vào thư mục `compose`

```bash
cd compose
```

### Bước 2: khởi động toàn bộ container hiện tại

```bash
docker compose up -d
```

### Bước 3: kiểm tra trạng thái container

```bash
docker compose ps
```

## 9. Các lệnh kiểm tra PostgreSQL

### Kiểm tra schema

```bash
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "\dn"
```

### Kiểm tra bảng trong schema `stock`

```bash
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "\dt stock.*"
```

### Query dữ liệu Kafka đã được Spark ghi vào PostgreSQL

```bash
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "SELECT id, symbol, price, topic, partition_id, kafka_offset, event_time, ingested_at FROM stock.kafka_ticks ORDER BY id DESC LIMIT 10;"
```

### Query bảng audit pipeline

```bash
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "SELECT id, run_id, checked_at, kafka_ok, spark_ok, minio_ok, postgres_ok, kafka_ticks_count, missing_tables, notes FROM stock.pipeline_audit ORDER BY id DESC LIMIT 10;"
```

### Kết quả mong đợi

- schema `stock`
- bảng `stock.predictions`
- bảng `stock.model_registry`
- bảng `stock.kafka_ticks`
- bảng `stock.pipeline_audit`
- dữ liệu mới do Spark ghi từ Kafka xuất hiện trong `stock.kafka_ticks`
- dữ liệu audit từ Airflow xuất hiện trong `stock.pipeline_audit`

Lưu ý: `compose/postgres/init/001_init.sql` hiện trong repo vẫn mới mô tả phần khởi tạo các bảng nền ban đầu. Nếu dựng môi trường hoàn toàn mới, cần bảo đảm `stock.kafka_ticks` và `stock.pipeline_audit` đã được tạo trước khi chạy các job tương ứng.

## 10. Các lệnh kiểm tra MinIO

### Health check

```bash
curl.exe -i http://localhost:9000/minio/health/live
```

### Mở giao diện web

Truy cập trình duyệt:

```text
http://localhost:9001
```

### Thông tin đăng nhập

Xem trong file:

```text
compose/.env
```

Nên đổi password mặc định trước khi dùng lâu dài.

## 11. Các lệnh kiểm tra Kafka

### Khởi động Kafka riêng

```bash
docker compose up -d kafka
```

### Kiểm tra log Kafka

```bash
docker compose logs kafka --tail=50
```

### Tạo topic test

```bash
docker exec -it ie212-kafka /opt/kafka/bin/kafka-topics.sh --create --topic stock-price --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
```

### Liệt kê topic

```bash
docker exec -it ie212-kafka /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092
```

### Gửi message bằng producer

```bash
docker exec -it ie212-kafka /opt/kafka/bin/kafka-console-producer.sh --topic stock-price --bootstrap-server localhost:9092
```

Ví dụ message:

```json
{"symbol":"AAPL","price":210.15}
{"symbol":"MSFT","price":438.20}
{"symbol":"AMD","price":167.05}
```

### Đọc message bằng consumer

```bash
docker exec -it ie212-kafka /opt/kafka/bin/kafka-console-consumer.sh --topic stock-price --from-beginning --bootstrap-server localhost:9092 --max-messages 3
```

### Kết quả mong đợi

Consumer đọc lại đúng message đã gửi vào topic `stock-price`.

## 12. Các lệnh kiểm tra Spark standalone

### Khởi động Spark

```bash
docker compose up -d spark-master spark-worker
```

### Kiểm tra trạng thái

```bash
docker compose ps
```

### Spark Master UI

```text
http://localhost:8080
```

### Spark Worker UI

```text
http://localhost:8081
```

### Chạy smoke test Spark

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 /opt/spark/jobs/simple_spark_check.py
```

### Kết quả mong đợi

- Spark Master và Spark Worker chạy ổn
- Worker đăng ký thành công với Master
- Job `ie212-spark-check` chạy thành công
- DataFrame hiển thị 3 dòng dữ liệu mẫu
- `Row count = 3`

## 13. Spark batch read từ Kafka

### File job

```text
services/spark/jobs/read_kafka_batch.py
```

### Chạy batch job

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2 /opt/spark/jobs/read_kafka_batch.py
```

### Chức năng

- đọc dữ liệu batch từ topic `stock-price`
- hiển thị schema gốc từ Kafka
- hiển thị raw message
- parse JSON trong cột `value`
- đếm số dòng dữ liệu đọc được

### Kết quả mong đợi

- thấy schema Kafka với các cột như `key`, `value`, `topic`, `partition`, `offset`, `timestamp`
- thấy dữ liệu raw từ Kafka
- parse được JSON thành các cột:
- `symbol`
- `price`
- `Row count = 3`

## 14. Spark Structured Streaming từ Kafka

### File job

```text
services/spark/jobs/read_kafka_stream.py
```

### Chạy stream job

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2 /opt/spark/jobs/read_kafka_stream.py
```

### Gửi thêm dữ liệu bằng Kafka producer

```bash
docker exec -it ie212-kafka /opt/kafka/bin/kafka-console-producer.sh --topic stock-price --bootstrap-server localhost:9092
```

Ví dụ:

```json
{"symbol":"NVDA","price":912.30}
{"symbol":"GOOGL","price":158.40}
{"symbol":"TSLA","price":171.25}
```

### Chức năng

- Spark lắng nghe dữ liệu mới từ Kafka
- parse JSON từ message
- in dữ liệu ra console theo từng micro-batch

### Kết quả mong đợi

- Spark in ra các batch mới khi Kafka nhận thêm message
- thấy các mã mới như `NVDA`, `GOOGL`, `TSLA`
- xác nhận luồng `Kafka -> Spark streaming` hoạt động

## 15. Spark Structured Streaming ghi sang PostgreSQL

### File job

```text
services/spark/jobs/write_kafka_stream_to_postgres.py
```

### Chạy stream job ghi PostgreSQL

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2,org.postgresql:postgresql:42.7.10 /opt/spark/jobs/write_kafka_stream_to_postgres.py
```

### Gửi thêm dữ liệu vào Kafka

```bash
docker exec -it ie212-kafka /opt/kafka/bin/kafka-console-producer.sh --topic stock-price --bootstrap-server localhost:9092
```

Ví dụ:

```json
{"symbol":"META","price":502.15}
{"symbol":"AMZN","price":189.40}
{"symbol":"NFLX","price":628.75}
```

### Kiểm tra dữ liệu đã được ghi vào PostgreSQL

```bash
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "SELECT id, symbol, price, topic, partition_id, kafka_offset, event_time, ingested_at FROM stock.kafka_ticks ORDER BY id DESC LIMIT 10;"
```

### Chức năng

- Spark đọc stream từ Kafka
- parse JSON
- dùng `foreachBatch` để ghi từng micro-batch vào PostgreSQL qua JDBC
- lưu dữ liệu vào bảng `stock.kafka_ticks`

### Kết quả mong đợi

- terminal Spark hiển thị:
- `Batch ... wrote ... rows to PostgreSQL`
- PostgreSQL query ra được các dòng mới như:
- `META`
- `AMZN`
- `NFLX`

## 16. Spark batch ghi Parquet và upload sang MinIO

### File job

```text
services/spark/jobs/write_kafka_batch_to_parquet.py
```

### Chạy batch job ghi Parquet

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2 /opt/spark/jobs/write_kafka_batch_to_parquet.py
```

### Kiểm tra file Parquet trên host

```powershell
Get-ChildItem services\spark\out\kafka_ticks_parquet -Recurse
```

### Upload Parquet lên MinIO

```bash
docker compose run --rm minio-client -c "mc alias set local http://minio:9000 minioadmin change_me_minio && mc cp --recursive /upload/kafka_ticks_parquet local/processed/kafka_ticks_parquet"
```

### Kiểm tra object trên MinIO

Có thể kiểm tra theo 2 cách.

Cách 1: qua MinIO UI

```text
http://localhost:9001
```

Vào bucket `processed` và kiểm tra thư mục `kafka_ticks_parquet`.

Cách 2: bằng `mc ls`

```bash
docker compose run --rm minio-client -c "mc alias set local http://minio:9000 minioadmin change_me_minio && mc ls --recursive local/processed/kafka_ticks_parquet"
```

### Chức năng

- Spark đọc dữ liệu Kafka theo batch
- parse JSON
- ghi ra file Parquet trong thư mục local mount
- dùng `mc` upload thư mục Parquet sang bucket `processed` của MinIO

### Kết quả mong đợi

- thấy file `part-...snappy.parquet` và `_SUCCESS` trong:
- `services/spark/out/kafka_ticks_parquet`
- MinIO bucket `processed` có thư mục:
- `kafka_ticks_parquet`

## 17. Airflow setup và kiểm tra

### Tạo thư mục Airflow

```powershell
New-Item -ItemType Directory -Path airflow\dags -Force
New-Item -ItemType Directory -Path airflow\logs -Force
New-Item -ItemType Directory -Path airflow\plugins -Force
```

### Service Airflow hiện có

- `ie212-airflow-apiserver`
- `ie212-airflow-scheduler`
- `ie212-airflow-dag-processor`
- `ie212-airflow-triggerer`

### Kiểm tra trạng thái

```bash
docker compose ps
```

### Xem log apiserver để lấy password simple auth

```bash
docker compose logs airflow-apiserver --tail=200
```

### Mở UI Airflow

```text
http://localhost:8088
```

### DAG smoke test

File:

```text
airflow/dags/ie212_smoke_test.py
```

Chức năng:

- kiểm tra Airflow stack chạy được
- trigger thủ công trong UI
- 2 task `hello` và `summary` chạy thành công

### DAG pipeline thật

File:

```text
airflow/dags/ie212_data_pipeline.py
```

Chức năng:

- đảm bảo bảng `stock.pipeline_audit` tồn tại
- kiểm tra Kafka
- kiểm tra Spark Master
- kiểm tra MinIO
- kiểm tra PostgreSQL
- ghi audit row vào `stock.pipeline_audit`
- xác nhận pipeline cơ bản đang sống

### Kiểm tra audit do Airflow ghi

```bash
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "SELECT id, run_id, checked_at, kafka_ok, spark_ok, minio_ok, postgres_ok, kafka_ticks_count, missing_tables, notes FROM stock.pipeline_audit ORDER BY id DESC LIMIT 10;"
```

### Kết quả mong đợi

- login Airflow UI thành công
- DAG `ie212_smoke_test` chạy thành công
- DAG `ie212_data_pipeline` chạy thành công
- bảng `stock.pipeline_audit` có row audit mới
- các cột `kafka_ok`, `spark_ok`, `minio_ok`, `postgres_ok` đều là `true`

## 18. Các lệnh quản lý Docker Compose

### Xem service đang chạy

```bash
docker compose ps
```

### Xem cả container đã thoát

```bash
docker compose ps -a
```

### Xem log PostgreSQL

```bash
docker compose logs postgres
```

### Xem log MinIO

```bash
docker compose logs minio
```

### Xem log Kafka

```bash
docker compose logs kafka
```

### Xem log Spark Master

```bash
docker compose logs spark-master
```

### Xem log Spark Worker

```bash
docker compose logs spark-worker
```

### Xem log Airflow API Server

```bash
docker compose logs airflow-apiserver
```

### Xem log Airflow Scheduler

```bash
docker compose logs airflow-scheduler
```

### Tắt hệ thống

```bash
docker compose down
```

### Tắt và xóa luôn volume dữ liệu

```bash
docker compose down -v
```

`Cẩn thận:` `down -v` sẽ xóa dữ liệu PostgreSQL, MinIO và các volume liên quan.

## 19. Những gì đã xác nhận thành công

### Local ML

- notebook chạy được
- code sau khi tách vẫn chạy ổn
- experiment chạy ngoài notebook thành công
- checkpoint model đã lưu thành công
- checkpoint đã load lại thành công

### Big Data - Storage

- PostgreSQL container chạy healthy
- schema `stock` đã được tạo
- bảng `predictions`, `model_registry`, `kafka_ticks`, `pipeline_audit` đã được tạo
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
- `Kafka -> Spark -> PostgreSQL` pipeline cơ bản đã hoạt động
- `Kafka -> Spark -> MinIO` pipeline cơ bản đã hoạt động

### Big Data - Orchestration

- Airflow API Server, Scheduler, Dag Processor, Triggerer chạy ổn
- Airflow UI login thành công
- DAG `ie212_smoke_test` chạy thành công
- DAG `ie212_data_pipeline` chạy thành công
- Airflow ghi audit vào `stock.pipeline_audit` thành công

## 20. Bước tiếp theo

Roadmap tiếp theo của project là:

- viết DAG orchestration mạnh hơn để gọi Spark jobs thực tế
- tạo DAG full pipeline:
- check service
- chạy Spark write PostgreSQL
- chạy Spark write Parquet
- upload MinIO
- ghi audit cuối pipeline
- dựng `FastAPI` để serving model
- tích hợp model local hiện tại vào hệ thống Big Data end-to-end

## 21. Ghi chú

- local ML phase hiện đã hoàn thành ở mức đủ tốt để chuyển sang hạ tầng
- Big Data phase hiện đã hoàn thành:
- storage layer đầu tiên
- streaming layer đầu tiên
- processing layer đầu tiên
- sink vào PostgreSQL
- sink vào MinIO
- orchestration cơ bản bằng Airflow
- đây là checkpoint rất tốt trước khi sang DAG full pipeline và model serving

## 22. Quick start ngắn gọn

### Local ML

```powershell
.\.venv\Scripts\Activate.ps1
python -m scripts.run_experiment
python -m scripts.test_load_checkpoint
```

### Big Data services

```bash
cd compose
docker compose up -d
docker compose ps
```

### Kiểm tra PostgreSQL

```bash
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "\dn"
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "\dt stock.*"
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "SELECT id, symbol, price, topic, partition_id, kafka_offset, event_time, ingested_at FROM stock.kafka_ticks ORDER BY id DESC LIMIT 10;"
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "SELECT id, run_id, checked_at, kafka_ok, spark_ok, minio_ok, postgres_ok, kafka_ticks_count, missing_tables, notes FROM stock.pipeline_audit ORDER BY id DESC LIMIT 10;"
```

### Kiểm tra Kafka

```bash
docker exec -it ie212-kafka /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092
docker exec -it ie212-kafka /opt/kafka/bin/kafka-console-consumer.sh --topic stock-price --from-beginning --bootstrap-server localhost:9092 --max-messages 3
```

### Kiểm tra Spark batch

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2 /opt/spark/jobs/read_kafka_batch.py
```

### Kiểm tra Spark stream

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2 /opt/spark/jobs/read_kafka_stream.py
```

### Kiểm tra Spark stream ghi PostgreSQL

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2,org.postgresql:postgresql:42.7.10 /opt/spark/jobs/write_kafka_stream_to_postgres.py
```

### Kiểm tra Spark batch ghi Parquet và upload MinIO

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2 /opt/spark/jobs/write_kafka_batch_to_parquet.py
docker compose run --rm minio-client -c "mc alias set local http://minio:9000 minioadmin change_me_minio && mc cp --recursive /upload/kafka_ticks_parquet local/processed/kafka_ticks_parquet"
```

### Kiểm tra Airflow

```bash
docker compose logs airflow-apiserver --tail=200
docker compose logs airflow-scheduler --tail=200
```

### UI

```text
MinIO: http://localhost:9001
Spark Master: http://localhost:8080
Spark Worker: http://localhost:8081
Airflow: http://localhost:8088
```

## 23. Mục đích project

Project phục vụ:

- tái hiện và cải tiến bài toán dự đoán giá cổ phiếu bằng mô hình hybrid temporal-relational
- triển khai pipeline Big Data end-to-end cho đồ án môn IE212
- làm nền tảng để tích hợp Spark, Kafka, Airflow, FastAPI và model serving trong các bước tiếp theo
