# IE212 - Stock Price Prediction with Local ML Pipeline and Big Data Roadmap

## 1. Giới thiệu

Đây là project môn `IE212 - Công nghệ dữ liệu lớn`, tập trung vào bài toán dự đoán giá cổ phiếu bằng mô hình lai giữa `LSTM` và `GNN`, sau đó từng bước tích hợp mô hình vào một hệ thống Big Data hoàn chỉnh.

Project hiện được triển khai theo 2 giai đoạn chính:

- `Giai đoạn 1 - Local ML Project`
  - chạy notebook nghiên cứu
  - tách code khỏi notebook thành project Python có cấu trúc
  - chạy experiment ngoài notebook
  - lưu checkpoint model
  - kiểm tra load lại checkpoint
- `Giai đoạn 2 - Big Data System`
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
  - các bước tiếp theo sẽ là:
    - ghi dữ liệu Spark sang MinIO
    - `Airflow`
    - `FastAPI`
    - tích hợp model vào pipeline Big Data

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
- PostgreSQL đã được khởi tạo:
  - schema `stock`
  - bảng `stock.predictions`
  - bảng `stock.model_registry`
  - bảng `stock.kafka_ticks`
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

## 3. Cấu trúc thư mục hiện tại

```text
IE212/
├── .venv/
├── compose/
│   ├── compose.yaml
│   ├── .env
│   └── postgres/
│       └── init/
│           └── 001_init.sql
├── services/
│   └── spark/
│       └── jobs/
│           ├── simple_spark_check.py
│           ├── read_kafka_batch.py
│           ├── read_kafka_stream.py
│           └── write_kafka_stream_to_postgres.py
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
- `compose/postgres/init/001_init.sql`: SQL khởi tạo schema và các bảng PostgreSQL ban đầu
- `services/spark/jobs/`: các job Spark dùng để smoke test, đọc batch, đọc stream và ghi dữ liệu sang PostgreSQL

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
- `test_prepare_step`: kiểm tra train, val, test pack cho từng expanding step
- `run_experiment`: chạy thực nghiệm ngoài notebook
- `test_load_checkpoint`: kiểm tra load lại checkpoint đã lưu

## 6. Big Data phase - Storage, Streaming, Processing

Hiện tại project đã dựng thành công các service Big Data đầu tiên bằng Docker Compose:

### Storage layer

- `PostgreSQL`
- `MinIO`

### Streaming layer

- `Kafka`

### Processing layer

- `Spark Master`
- `Spark Worker`

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

### Kết quả mong đợi

- schema `stock`
- bảng `stock.predictions`
- bảng `stock.model_registry`
- bảng `stock.kafka_ticks`
- dữ liệu mới do Spark ghi từ Kafka sẽ xuất hiện trong `stock.kafka_ticks`

Lưu ý: file `compose/postgres/init/001_init.sql` trong repo hiện đang khởi tạo các bảng nền ban đầu. Nếu bạn dựng môi trường mới hoàn toàn, hãy bảo đảm bảng `stock.kafka_ticks` cũng đã được tạo trước khi chạy job stream ghi PostgreSQL.

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
- job `ie212-spark-check` chạy thành công
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

- terminal Spark hiển thị: `Batch ... wrote ... rows to PostgreSQL`
- PostgreSQL query ra được các dòng mới như:
  - `META`
  - `AMZN`
  - `NFLX`

## 16. Các lệnh quản lý Docker Compose

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

### Tắt hệ thống

```bash
docker compose down
```

### Tắt và xóa luôn volume dữ liệu

```bash
docker compose down -v
```

`Cẩn thận:` `down -v` sẽ xóa dữ liệu PostgreSQL, MinIO và các volume liên quan.

## 17. Những gì đã xác nhận thành công

### Local ML

- notebook chạy được
- code sau khi tách vẫn chạy ổn
- experiment chạy ngoài notebook thành công
- checkpoint model đã lưu thành công
- checkpoint đã load lại thành công

### Big Data - Storage

- PostgreSQL container chạy healthy
- schema `stock` đã được tạo
- bảng `predictions`, `model_registry`, `kafka_ticks` đã được tạo
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
- pipeline cơ bản `Kafka -> Spark -> PostgreSQL` đã hoạt động

## 18. Bước tiếp theo

Roadmap tiếp theo của project là:

- cho Spark ghi dữ liệu sang MinIO
- xây pipeline dữ liệu trung gian để chuẩn bị cho model serving
- dựng `Airflow` để orchestration pipeline
- dựng `FastAPI` để serving model
- tích hợp model local hiện tại vào hệ thống Big Data end-to-end

## 19. Ghi chú

- local ML phase hiện đã hoàn thành ở mức đủ tốt để chuyển sang hạ tầng
- Big Data phase hiện đã hoàn thành:
  - storage layer đầu tiên
  - streaming layer đầu tiên
  - processing layer đầu tiên
  - sink đầu tiên vào PostgreSQL
- đây là checkpoint rất tốt trước khi sang object storage sink hoặc orchestration

## 20. Quick start ngắn gọn

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

### UI

```text
MinIO: http://localhost:9001
Spark Master: http://localhost:8080
Spark Worker: http://localhost:8081
```

## 21. Mục đích project

Project phục vụ:

- tái hiện và cải tiến bài toán dự đoán giá cổ phiếu bằng mô hình hybrid temporal-relational
- triển khai pipeline Big Data end-to-end cho đồ án môn IE212
- làm nền tảng để tích hợp Spark, Kafka, Airflow, FastAPI và model serving trong các bước tiếp theo
