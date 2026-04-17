# IE212 - Hướng dẫn chạy hệ thống

README này chỉ tập trung vào một mục tiêu: `chạy hệ thống theo đúng thứ tự, ít nhầm lẫn nhất`.

## 1. Luồng chính của hệ thống

```text
yfinance hoặc data/raw CSV
-> stock-producer
-> Kafka topic stock-price
-> Spark batch
-> PostgreSQL / parquet
-> MinIO / Airflow validation
-> FastAPI dashboard
```

Ghi chú quan trọng:

- Với trạng thái hiện tại của project, `Kafka đang được dùng theo batch path`.
- Luồng demo chính nên bám theo:
  - `ie212_kafka_end_to_end_smoke_test`
  - `ie212_spark_exec_pipeline`
  - `ie212_data_pipeline`
- Không nên lấy `stock.kafka_ticks` làm luồng demo chính nữa.

## 2. Cần mở gì trước khi chạy?

Bạn nên mở:

- `Terminal 1`: để chạy Docker stack
- `Terminal 2`: để chạy lệnh local như train, producer, save inference
- `Browser`: để mở Airflow / dashboard / docs

## 3. Chuẩn bị môi trường

### 3.1. Clone và cài Python dependencies

```powershell
git clone <repo-url>
cd ie212

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3.2. Tạo file env cho Docker

```powershell
Copy-Item compose\.env.example compose\.env
```

## 4. Chạy local ML trước

Chạy ở `Terminal 2`:

### 4.1. Tải dữ liệu raw

```powershell
python scripts/run_train.py
```

### 4.2. Train model

```powershell
python scripts/run_experiment.py
```

### 4.3. Tạo inference bundle

```powershell
python scripts/build_latest_inference_bundle.py --data-dir data/raw --output data/inference/latest_window.npz
```

### 4.4. Chạy inference local

```powershell
python scripts/run_checkpoint_inference.py --checkpoint models/hybrid_expanding_best_full.pt --input-npz data/inference/latest_window.npz --output-json outputs/inference/latest_prediction.json
```

## 5. Khởi động Big Data stack

Chạy ở `Terminal 1`:

### 5.1. Build Airflow image

```powershell
docker build -t ie212-airflow-custom:local -f airflow/Dockerfile .
```

### 5.2. Start toàn bộ stack

```powershell
docker compose --env-file compose/.env -f compose/compose.yaml --profile producer up -d --build
```

## 6. Mở các địa chỉ cần thiết

Mở ở `Browser`:

- Airflow UI: [http://localhost:8088](http://localhost:8088)
- FastAPI docs: [http://localhost:8008/docs](http://localhost:8008/docs)
- Dashboard: [http://localhost:8008/dashboard](http://localhost:8008/dashboard)
- Spark Master UI: [http://localhost:8080](http://localhost:8080)
- Spark Worker UI: [http://localhost:8081](http://localhost:8081)
- MinIO Console: [http://localhost:9001](http://localhost:9001)

## 7. Đăng nhập Airflow

Airflow hiện dùng `SimpleAuthManager`.

Tài khoản `không cố định` theo kiểu `airflow / airflow`.
Username có thể cấu hình được, nhưng password thật được Airflow tự sinh.

### 7.1. Kiểm tra username đang dùng

```powershell
docker exec ie212-airflow-apiserver airflow config get-value core simple_auth_manager_users
```

Ví dụ nếu kết quả là:

```text
admin:admin
```

thì:

- username là `admin`
- role là `admin`

### 7.2. Lấy password thật

```powershell
docker exec ie212-airflow-apiserver cat /opt/airflow/simple_auth_manager_passwords.json.generated
```

Ví dụ nếu kết quả là:

```json
{"admin": "DW4was43Wr2qvVKE"}
```

thì dùng:

- username: `admin`
- password: `DW4was43Wr2qvVKE`

## 8. Kafka: bạn cần chạy lệnh nào?

Nếu bạn đã start Docker với `--profile producer`, thì `stock-producer` đã chạy rồi.

Tuy nhiên để demo dễ kiểm soát, mình khuyên vẫn chạy one-shot ở `Terminal 2`:

```powershell
python scripts/publish_stock_ticks.py --bootstrap-servers localhost:29092 --source auto --max-iterations 1
```

Nếu không có internet nhưng đã có `data/raw/*.csv`:

```powershell
python scripts/publish_stock_ticks.py --bootstrap-servers localhost:29092 --source csv --max-iterations 1
```

## 9. Airflow: chạy DAG nào?

Với hướng demo hiện tại, hãy chạy theo đúng thứ tự sau:

### 9.1. DAG 1 - Kafka smoke test

Vào Airflow:

1. Mở [http://localhost:8088](http://localhost:8088)
2. Đăng nhập bằng username/password thật đã lấy ở bước 7
3. Tìm DAG `ie212_kafka_end_to_end_smoke_test`
4. Nếu DAG đang `Paused`, bật sang `On`
5. Bấm vào tên DAG
6. Bấm `Trigger DAG`

DAG này sẽ:

1. gọi producer one-shot
2. gọi Spark batch đọc Kafka
3. ghi vào `stock.kafka_ticks_batch`
4. validate bảng này trong PostgreSQL

Nếu DAG này chạy xanh, nghĩa là Kafka đã tham gia đúng vào pipeline.

### 9.2. DAG 2 - Spark exec pipeline

Sau đó chạy:

- `ie212_spark_exec_pipeline`

DAG này sẽ:

1. đọc Kafka batch
2. ghi vào `stock.kafka_ticks_batch`
3. ghi parquet
4. upload parquet lên MinIO
5. ghi audit

### 9.3. DAG 3 - Data pipeline

Cuối cùng mới chạy:

- `ie212_data_pipeline`

Lưu ý:

- Sau khi đã chọn hướng 2, DAG này bây giờ validate theo `stock.kafka_ticks_batch`
- Nghĩa là bạn `không nên` chạy DAG này trước Kafka smoke test hoặc Spark exec pipeline

## 10. Đưa inference vào PostgreSQL

Chạy ở `Terminal 2`:

```powershell
python scripts/save_inference_to_postgres.py --input-json outputs/inference/latest_prediction.json --pg-host localhost --pg-port 15432 --pg-db stock_project --pg-user stock_user --pg-password change_me_postgres
```

## 11. Xem dashboard

Mở:

- Dashboard: [http://localhost:8008/dashboard](http://localhost:8008/dashboard)
- API docs: [http://localhost:8008/docs](http://localhost:8008/docs)

## 12. Luồng chạy ngắn gọn nhất

Nếu bạn chỉ muốn một chuỗi lệnh rõ ràng, hãy làm đúng thứ tự này:

### Terminal 1

```powershell
Copy-Item compose\.env.example compose\.env
docker build -t ie212-airflow-custom:local -f airflow/Dockerfile .
docker compose --env-file compose/.env -f compose/compose.yaml --profile producer up -d --build
```

### Terminal 2

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/run_train.py
python scripts/run_experiment.py
python scripts/build_latest_inference_bundle.py --data-dir data/raw --output data/inference/latest_window.npz
python scripts/run_checkpoint_inference.py --checkpoint models/hybrid_expanding_best_full.pt --input-npz data/inference/latest_window.npz --output-json outputs/inference/latest_prediction.json
python scripts/publish_stock_ticks.py --bootstrap-servers localhost:29092 --source auto --max-iterations 1
python scripts/save_inference_to_postgres.py --input-json outputs/inference/latest_prediction.json --pg-host localhost --pg-port 15432 --pg-db stock_project --pg-user stock_user --pg-password change_me_postgres
```

### Browser

1. mở [http://localhost:8088](http://localhost:8088)
2. đăng nhập bằng username/password thật ở bước 7
3. trigger DAG `ie212_kafka_end_to_end_smoke_test`
4. trigger DAG `ie212_spark_exec_pipeline`
5. trigger DAG `ie212_data_pipeline`
6. mở [http://localhost:8008/dashboard](http://localhost:8008/dashboard)

## 13. Reset workspace

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\reset_workspace.ps1
```

Nếu muốn xóa luôn `.venv`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\reset_workspace.ps1 -RemoveVenv
```

Reset hiện tại đã bao phủ luôn phần Kafka:

- dừng stack thường
- dừng stack `--profile producer`
- xóa `data/raw`, `data/processed`, `data/inference`, `models`
- xóa toàn bộ `outputs`
- xóa `services/spark/out`
- xóa Airflow logs
- xóa `__pycache__`

## 14. Ghi chú ngắn

- PostgreSQL host port là `15432`
- Kafka host port là `29092`
- nếu không có internet thì producer nên dùng `--source csv`
- nếu `data/raw/*.csv` chưa có thì hãy chạy `python scripts/run_train.py` trước
