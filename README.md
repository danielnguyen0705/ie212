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
  - bắt đầu từ storage layer:
    - `PostgreSQL`
    - `MinIO`
  - sau đó mở rộng sang streaming layer:
    - `Kafka`
  - tiếp tục sang processing layer:
    - `Spark`
  - các bước tiếp theo sẽ là:
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
  - `Spark standalone`
- PostgreSQL đã được khởi tạo:
  - schema `stock`
  - bảng `stock.predictions`
  - bảng `stock.model_registry`
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
  - chạy `spark-master` và `spark-worker`
  - worker đăng ký thành công với master
  - chạy `spark-submit` thành công
  - job test đọc dữ liệu mẫu và in ra `Row count = 3`

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
│           └── simple_spark_check.py
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
- `services/spark/jobs/simple_spark_check.py`: job Spark dùng để smoke test processing layer

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

## 6. Big Data phase - Storage, Streaming và Processing layer đầu tiên

Hiện tại project đã dựng thành công 5 service đầu tiên bằng Docker Compose:

- `PostgreSQL`: lưu metadata, prediction results, model registry
- `MinIO`: object storage kiểu S3 cho raw data, processed data, models, artifacts
- `Kafka`: message broker cho data streaming và event-driven pipeline
- `Spark Master`: điều phối job Spark standalone
- `Spark Worker`: thực thi job Spark và đăng ký với master

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

### File job Spark test

- `services/spark/jobs/simple_spark_check.py`

## 8. Cách chạy các service hiện tại

### Bước 1: đi vào thư mục `compose`

```bash
cd compose
```

### Bước 2: khởi động các container

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

### Kết quả mong đợi

- schema `stock`
- bảng `stock.predictions`
- bảng `stock.model_registry`

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

Ví dụ hiện tại:

```text
user: minioadmin
password: change_me_minio
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

Consumer đọc lại đúng 3 message đã gửi vào topic `stock-price`.

## 12. Các lệnh quản lý Docker Compose

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

`Cẩn thận:` `down -v` sẽ xóa dữ liệu PostgreSQL và MinIO local.

## 13. Big Data phase - Processing layer đầu tiên

Project hiện đã dựng thành công thêm `Spark standalone` bằng Docker Compose.

### Service Spark hiện có

- `ie212-spark-master`
- `ie212-spark-worker`

### File job test

- `services/spark/jobs/simple_spark_check.py`

### Những gì đã kiểm tra thành công

- Spark Master UI truy cập được tại `http://localhost:8080`
- Spark Worker UI truy cập được tại `http://localhost:8081`
- Worker đã đăng ký thành công với master
- Chạy `spark-submit` thành công
- Spark đọc được dữ liệu mẫu và in ra DataFrame 3 dòng
- `Row count = 3`

### Lệnh chạy Spark

Khởi động Spark:

```powershell
docker compose up -d spark-master spark-worker
```

Kiểm tra trạng thái:

```bash
docker compose ps
```

Chạy job test:

```bash
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 /opt/spark/jobs/simple_spark_check.py
```

### Kết quả mong đợi

- thấy Spark Master và Spark Worker đang chạy
- vào được `localhost:8080`
- vào được `localhost:8081`
- job `ie212-spark-check` chạy thành công
- output hiển thị 3 dòng dữ liệu mẫu và row count bằng 3

## 14. Những gì đã xác nhận thành công

### Local ML

- notebook chạy được
- code sau khi tách vẫn chạy ổn
- experiment chạy ngoài notebook thành công
- checkpoint model đã lưu thành công
- checkpoint đã load lại thành công

### Big Data - Storage

- PostgreSQL container chạy healthy
- schema `stock` đã được tạo
- bảng `predictions` và `model_registry` đã được tạo
- MinIO web UI truy cập được
- bucket `raw`, `processed`, `models`, `artifacts` đã được tạo

### Big Data - Streaming

- Kafka container chạy healthy
- topic `stock-price` đã được tạo
- producer gửi được message
- consumer đọc lại được message
- smoke test Kafka thành công

### Big Data - Processing

- Spark Master UI truy cập được
- Spark Worker UI truy cập được
- Spark Worker đã đăng ký với Spark Master
- `spark-submit` chạy thành công
- job test đọc được dữ liệu mẫu
- kết quả `Row count = 3`

## 15. Bước tiếp theo

Roadmap tiếp theo của project là:

- xử lý dữ liệu batch bằng Spark
- kết nối Spark với Kafka
- dựng `Airflow` để orchestration pipeline
- dựng `FastAPI` để serving model
- tích hợp model local hiện tại vào hệ thống Big Data

## 16. Ghi chú

- local ML phase hiện đã hoàn thành ở mức đủ tốt để chuyển sang hạ tầng
- Big Data phase hiện đã hoàn thành:
  - storage layer đầu tiên
  - streaming layer đầu tiên
  - processing layer đầu tiên
- đây là checkpoint rất tốt trước khi sang bước tiếp theo

## 17. Quick start ngắn gọn

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
```

### Kiểm tra MinIO

```bash
curl.exe -i http://localhost:9000/minio/health/live
```

### Kiểm tra Kafka

```bash
docker exec -it ie212-kafka /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092
docker exec -it ie212-kafka /opt/kafka/bin/kafka-console-consumer.sh --topic stock-price --from-beginning --bootstrap-server localhost:9092 --max-messages 3
```

### Kiểm tra Spark

```bash
docker compose up -d spark-master spark-worker
docker exec -it ie212-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 /opt/spark/jobs/simple_spark_check.py
```

### MinIO UI

```text
http://localhost:9001
```

### Spark UI

```text
http://localhost:8080
http://localhost:8081
```

## 18. Mục đích project

Project phục vụ:

- tái hiện và cải tiến bài toán dự đoán giá cổ phiếu bằng mô hình hybrid temporal-relational
- triển khai pipeline Big Data end-to-end cho đồ án môn IE212
- làm nền tảng để tích hợp Spark, Kafka, Airflow, FastAPI và model serving trong các bước tiếp theo
