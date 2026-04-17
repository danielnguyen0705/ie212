# IE212 - Dự Án Dự Báo Giá Cổ Phiếu Với ML Cục Bộ Và Big Data Stack

Project này có 2 phần gắn liền với nhau:

1. `Local ML pipeline` để tải dữ liệu, huấn luyện mô hình, tạo checkpoint và sinh kết quả suy luận.
2. `Big Data pipeline` để đưa dữ liệu vào Kafka, xử lý bằng Spark, lưu vào PostgreSQL / MinIO, điều phối bằng Airflow và phục vụ qua FastAPI dashboard.

README này được viết theo `luồng chạy end-to-end`, để Kafka nằm đúng vai trò trong kiến trúc hệ thống thay vì bị tách rời ở cuối.

## Kiến trúc tổng quan

![System Architecture](img/system_architecture.png)

## Kafka đóng góp gì trong hệ thống?

Trong dự án này, Kafka là `ingestion layer` của hệ thống Big Data:

- `stock-producer` lấy giá từ `yfinance` hoặc fallback từ `data/raw/*.csv`
- producer đẩy message vào topic `stock-price`
- Spark đọc topic `stock-price` theo 2 hướng:
  - `streaming` -> ghi vào `stock.kafka_ticks`
  - `batch` -> ghi vào `stock.kafka_ticks_batch` và parquet
- parquet được upload lên MinIO
- Airflow điều phối và validate pipeline
- FastAPI / dashboard đọc dữ liệu đã xử lý từ PostgreSQL

Luồng logic:

```text
yfinance hoặc data/raw CSV
    -> stock-producer
    -> Kafka topic stock-price
    -> Spark stream/batch jobs
    -> PostgreSQL + Parquet
    -> MinIO + Airflow validation
    -> FastAPI / dashboard
```

## Cấu trúc thư mục quan trọng

```text
IE212/
|-- airflow/                  # Dockerfile + DAG Airflow
|-- compose/                  # Docker Compose + env mẫu
|-- data/
|   |-- inference/            # inference bundle .npz
|   |-- raw/                  # CSV raw cho local pipeline và producer fallback
|   `-- processed/            # dữ liệu xử lý trung gian
|-- img/
|   `-- system_architecture.png
|-- models/                   # checkpoint sinh ra sau khi train
|-- outputs/                  # metrics, predictions, reports
|-- scripts/                  # train / infer / producer / save DB / reset
|-- services/
|   |-- api/                  # FastAPI + dashboard
|   |-- inference/            # Docker image cho ML runner
|   |-- producer/             # Docker image cho Kafka stock producer
|   `-- spark/                # Spark jobs
|-- src/                      # ML core code
|-- README.md
`-- requirements.txt
```

## Yêu cầu trước khi chạy

- Windows PowerShell
- Python 3.11
- Docker Desktop
- Git

## 1. Clone project và tạo môi trường

```powershell
git clone <repo-url>
cd ie212

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 2. Giai đoạn A - Chuẩn bị local ML assets

Giai đoạn này tạo raw data, checkpoint và inference bundle. Đây là phần nên làm trước nếu bạn muốn:

- có raw CSV cho dashboard và producer fallback
- có checkpoint cho `ml-infer`
- có inference JSON để đẩy vào PostgreSQL

### A1. Tải raw CSV về `data/raw`

```powershell
python scripts/run_train.py
```

Hành vi:

- nếu `data/raw/<TICKER>.csv` đã có thì ưu tiên dùng lại
- nếu chưa có thì tải từ `yfinance`
- nếu muốn tải lại toàn bộ:

```powershell
python scripts/run_train.py --refresh
```

### A2. Train và sinh checkpoint

```powershell
python scripts/run_experiment.py
```

Output chính:

- `models/lstm_expanding_best_full.pt`
- `models/hybrid_expanding_best_full.pt`
- `models/run_metadata_full.json`
- `outputs/metrics_full.json`

### A3. Build inference bundle

```powershell
python scripts/build_latest_inference_bundle.py --data-dir data/raw --output data/inference/latest_window.npz
```

### A4. Chạy local inference

```powershell
python scripts/run_checkpoint_inference.py --checkpoint models/hybrid_expanding_best_full.pt --input-npz data/inference/latest_window.npz --output-json outputs/inference/latest_prediction.json
```

### A5. Kiểm tra checkpoint nếu cần

```powershell
python scripts/inspect_checkpoint.py --checkpoint models/hybrid_expanding_best_full.pt
```

## 3. Giai đoạn B - Khởi động Big Data stack

### B1. Tạo `compose/.env`

```powershell
Copy-Item compose\.env.example compose\.env
```

### B2. Build Airflow image local

```powershell
docker build -t ie212-airflow-custom:local -f airflow/Dockerfile .
```

### B3. Start stack có Kafka / Spark / MinIO / PostgreSQL / Airflow / FastAPI

Stack mặc định:

```powershell
docker compose --env-file compose/.env -f compose/compose.yaml up -d --build
```

Nếu muốn bật thêm producer service:

```powershell
docker compose --env-file compose/.env -f compose/compose.yaml --profile producer up -d --build
```

Service chính:

- PostgreSQL: `localhost:15432`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`
- Kafka host port: `localhost:29092`
- Spark Master UI: `http://localhost:8080`
- Spark Worker UI: `http://localhost:8081`
- Airflow UI: `http://localhost:8088`
- FastAPI docs: `http://localhost:8008/docs`
- Dashboard: `http://localhost:8008/dashboard`

## 4. Giai đoạn C - Đưa dữ liệu vào Kafka

Đây là bước làm cho Kafka trở thành một phần thật sự của hệ thống.

### C1. Chạy local producer

```powershell
python scripts/publish_stock_ticks.py --bootstrap-servers localhost:29092 --source auto
```

Lựa chọn source:

- `--source auto`: thử `yfinance` trước, nếu thất bại thì fallback sang `data/raw/*.csv`
- `--source yfinance`: chỉ lấy dữ liệu từ `yfinance`
- `--source csv`: chỉ replay từ `data/raw/*.csv`

Ví dụ one-shot:

```powershell
python scripts/publish_stock_ticks.py --bootstrap-servers localhost:29092 --source csv --max-iterations 1
```

### C2. Hoặc chạy producer service trong Docker

```powershell
docker compose --env-file compose/.env -f compose/compose.yaml --profile producer up -d stock-producer
```

## 5. Giai đoạn D - Xử lý dữ liệu từ Kafka bằng Spark

Sau khi producer đã đẩy dữ liệu vào topic `stock-price`, Spark là lớp xử lý chính.

### D1. Streaming path

Job:

- `services/spark/jobs/write_kafka_stream_to_postgres.py`

Vai trò:

- đọc topic `stock-price`
- parse JSON `{symbol, price}`
- append vào `stock.kafka_ticks`

### D2. Batch path

Job:

- `services/spark/jobs/write_kafka_batch_to_postgres.py`
- `services/spark/jobs/write_kafka_batch_to_parquet.py`

Vai trò:

- snapshot dữ liệu Kafka từ `earliest` đến `latest`
- ghi vào `stock.kafka_ticks_batch`
- ghi parquet ra `services/spark/out/kafka_ticks_parquet`

## 6. Giai đoạn E - Upload parquet và validation bằng Airflow

Airflow là lớp orchestration + validation, không phải nơi xử lý data thay Spark.

DAGs quan trọng:

- `ie212_data_pipeline`
  - check Kafka / Spark / MinIO / PostgreSQL
  - check `stock.kafka_ticks`
  - ghi `stock.pipeline_audit`
- `ie212_spark_exec_pipeline`
  - Spark batch -> PostgreSQL
  - Spark batch -> parquet
  - upload parquet -> MinIO
  - ghi audit
- `ie212_kafka_end_to_end_smoke_test`
  - one-shot producer -> Kafka
  - Spark batch -> PostgreSQL
  - validate `stock.kafka_ticks_batch`
- `ie212_end_to_end_inference_pipeline`
  - build bundle
  - run inference
  - save prediction vào PostgreSQL
  - validate kết quả

### Chạy smoke test end-to-end cho Kafka

Điều kiện:

- stack đã chạy
- nếu dùng DAG này thì `stock-producer` phải đang chạy, tức là bật compose với `--profile producer`

DAG:

- `ie212_kafka_end_to_end_smoke_test`

Mục đích:

1. producer đẩy message vào Kafka
2. Spark batch đọc Kafka và ghi vào `stock.kafka_ticks_batch`
3. validate bằng DB

## 7. Giai đoạn F - Inference và serving

### F1. Đưa kết quả inference vào PostgreSQL

Nếu bạn đã có `outputs/inference/latest_prediction.json`:

```powershell
python scripts/save_inference_to_postgres.py --input-json outputs/inference/latest_prediction.json --pg-host localhost --pg-port 15432 --pg-db stock_project --pg-user stock_user --pg-password change_me_postgres
```

Hoặc chạy trong container:

```powershell
docker exec ie212-ml-infer python scripts/save_inference_to_postgres.py --input-json outputs/inference/latest_prediction.json --pg-host postgres --pg-port 5432 --pg-db stock_project --pg-user stock_user --pg-password change_me_postgres
```

### F2. Xem dashboard và docs

- `http://localhost:8008/dashboard`
- `http://localhost:8008/docs`

FastAPI đọc prediction / metadata từ PostgreSQL, còn price history được đọc từ `data/raw/*.csv`.

## 8. Luồng demo mạch lạc để chạy lại từ đầu

Nếu bạn muốn demo đầy đủ hệ thống, thứ tự nên là:

1. Clone repo và tạo `.venv`
2. `pip install -r requirements.txt`
3. `python scripts/run_train.py`
4. `python scripts/run_experiment.py`
5. `python scripts/build_latest_inference_bundle.py --data-dir data/raw --output data/inference/latest_window.npz`
6. `python scripts/run_checkpoint_inference.py --checkpoint models/hybrid_expanding_best_full.pt --input-npz data/inference/latest_window.npz --output-json outputs/inference/latest_prediction.json`
7. `Copy-Item compose\.env.example compose\.env`
8. `docker build -t ie212-airflow-custom:local -f airflow/Dockerfile .`
9. `docker compose --env-file compose/.env -f compose/compose.yaml --profile producer up -d --build`
10. `python scripts/publish_stock_ticks.py --bootstrap-servers localhost:29092 --source auto --max-iterations 1`
11. Chạy DAG `ie212_kafka_end_to_end_smoke_test` hoặc `ie212_spark_exec_pipeline`
12. `python scripts/save_inference_to_postgres.py --input-json outputs/inference/latest_prediction.json --pg-host localhost --pg-port 15432 --pg-db stock_project --pg-user stock_user --pg-password change_me_postgres`
13. Mở dashboard và docs

Như vậy, Kafka nằm đúng giữa luồng Big Data:

```text
raw data / yfinance
    -> producer
    -> Kafka
    -> Spark
    -> PostgreSQL / parquet
    -> MinIO / Airflow validation
    -> FastAPI / dashboard
```

## 9. Reset workspace

Script reset:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\reset_workspace.ps1
```

Nếu muốn xóa luôn `.venv`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\reset_workspace.ps1 -RemoveVenv
```

Lệnh reset hiện tại sẽ:

- `docker compose down -v --remove-orphans`
- `docker compose --profile producer down -v --remove-orphans`
- xóa local ML artifacts trong `data/raw`, `data/processed`, `data/inference`, `models`
- xóa toàn bộ output trong `outputs/`
- xóa Spark local output trong `services/spark/out`
- xóa Airflow logs
- xóa Python `__pycache__`

Điều này có nghĩa là reset cũng đã bao phủ luôn phần Kafka flow mới:

- producer artifacts / fallback output
- parquet output sau khi Spark đọc Kafka
- named volumes của PostgreSQL / MinIO / Kafka stack
- container `stock-producer` nếu đang chạy qua profile `producer`

## 10. Ghi chú quan trọng

- `compose/.env` không được commit, hãy tạo từ `compose/.env.example`
- `5432` là port PostgreSQL nội bộ giữa container, host dùng `15432`
- dashboard cần `data/raw/*.csv` nếu bạn muốn xem price history
- nếu không có internet và cũng chưa có `data/raw/*.csv`, producer `--source auto` sẽ không có dữ liệu để đẩy vào Kafka
- `stock-producer` được đưa vào profile riêng để stack mặc định không bị phụ thuộc network feed
