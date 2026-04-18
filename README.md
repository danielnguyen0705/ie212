# IE212 - Hướng dẫn chạy hệ thống

README này ưu tiên 2 việc:

- chạy hệ thống đúng thứ tự, ít nhầm lẫn nhất
- hiểu rõ luồng `Kafka -> Spark -> model -> dashboard`

## 1. Kiến trúc tổng thể

Kiến trúc hiện tại gồm 5 lớp chính:

1. `Nguồn dữ liệu`
   - dữ liệu lịch sử lấy từ `yfinance`
   - hoặc đọc lại từ `data/raw/*.csv`

2. `Ingestion layer`
   - `stock-producer` lấy giá mới nhất
   - publish vào Kafka topic `stock-price`

3. `Big Data processing layer`
   - Spark đọc dữ liệu từ Kafka
   - ghi ra 2 nhánh:
     - `stock.kafka_ticks_batch` trong PostgreSQL
     - parquet trong `services/spark/out/kafka_ticks_parquet`

4. `Object storage + inference input layer`
   - parquet được đồng bộ lên MinIO
   - `build_kafka_inference_bundle.py` đọc parquet từ MinIO
   - tạo bundle `.npz` làm đầu vào cho model

5. `Inference + serving layer`
   - `run_checkpoint_inference.py` chạy checkpoint PyTorch
   - `save_inference_to_postgres.py` lưu kết quả vào `stock.inference_predictions`
   - FastAPI và dashboard đọc kết quả cuối từ PostgreSQL

Nếu viết lại thành một luồng dễ hình dung hơn thì hệ thống đang chạy như sau:

```text
Dữ liệu lịch sử
-> lưu ở data/raw
-> producer lấy giá mới
-> Kafka nhận dữ liệu online
-> Spark xử lý dữ liệu từ Kafka
-> Spark ghi batch table và parquet
-> parquet được upload lên MinIO
-> inference bundle được dựng từ parquet trong MinIO
-> model PyTorch chạy suy luận
-> prediction được lưu vào PostgreSQL
-> FastAPI / dashboard hiển thị kết quả
```

Điểm quan trọng:

- Project đang dùng `Kafka batch path` làm luồng demo chính.
- Prediction cuối cùng đã phụ thuộc vào dữ liệu đi qua Kafka.
- Không dùng `stock.kafka_ticks` làm trục demo chính nữa.

## 2. Cần mở gì trước khi chạy?

- `Terminal 1`: chạy Docker stack
- `Terminal 2`: chạy lệnh local
- `Browser`: mở Airflow, dashboard, docs

## 3. Chuẩn bị môi trường

### 3.1. Clone và cài Python dependencies

```powershell
git clone <repo-url>
cd ie212

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3.2. Tạo file env cho Docker

```powershell
Copy-Item compose\.env.example compose\.env
```

## 4. Chuẩn bị dữ liệu và model local

Chạy ở `Terminal 2`:

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/run_train.py
python scripts/run_experiment.py
```

Kết quả mong đợi:

- có `data/raw/*.csv`
- có checkpoint trong `models/`

## 5. Khởi động Big Data stack

Chạy ở `Terminal 1`:

```powershell
docker build -t ie212-airflow-custom:local -f airflow/Dockerfile .
docker compose --env-file compose/.env -f compose/compose.yaml --profile producer up -d --build
docker exec ie212-postgres psql -U stock_user -d postgres -c "CREATE DATABASE airflow_meta OWNER stock_user;"
docker compose --env-file compose/.env -f compose/compose.yaml up -d airflow-init
docker compose --env-file compose/.env -f compose/compose.yaml up -d airflow-apiserver airflow-scheduler airflow-dag-processor airflow-triggerer
docker compose --env-file compose/.env -f compose/compose.yaml ps
```

Kết quả mong đợi:

- `ie212-postgres`, `ie212-kafka`, `ie212-spark-master`, `ie212-spark-worker`, `ie212-ml-infer`, `ie212-fastapi` ở trạng thái `Up`
- các service `airflow-*` ở trạng thái `Up`
- có thể mở Airflow tại [http://localhost:8088](http://localhost:8088)

## 6. Các địa chỉ cần mở

- Airflow UI: [http://localhost:8088](http://localhost:8088)
- FastAPI docs: [http://localhost:8008/docs](http://localhost:8008/docs)
- Dashboard: [http://localhost:8008/dashboard](http://localhost:8008/dashboard)
- Spark Master UI: [http://localhost:8080](http://localhost:8080)
- Spark Worker UI: [http://localhost:8081](http://localhost:8081)
- MinIO Console: [http://localhost:9001](http://localhost:9001)

## 7. Đăng nhập Airflow

Lấy username:

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

Lấy password thật:

```powershell
docker exec ie212-airflow-apiserver cat /opt/airflow/simple_auth_manager_passwords.json.generated
```

Ví dụ:

```json
{"admin": "DW4was43Wr2qvVKE"}
```

thì dùng:

- username: `admin`
- password: `DW4was43Wr2qvVKE`

## 8. Kafka đang đóng góp như thế nào?

Trong project hiện tại, Kafka là `ingestion layer` của hệ thống.

Luồng cụ thể:

```text
producer
-> Kafka topic stock-price
-> Spark batch
-> stock.kafka_ticks_batch + parquet
-> MinIO
-> build_kafka_inference_bundle.py
-> run_checkpoint_inference.py
-> stock.inference_predictions
```

Nghĩa là:

- Kafka không đi thẳng vào model
- dữ liệu đi qua Kafka được Spark xử lý, ghi parquet và upload lên MinIO
- inference bundle được dựng từ parquet trong MinIO
- prediction cuối cùng đã bị ảnh hưởng bởi Kafka path

## 9. Lệnh Kafka cần chạy

Nếu bạn đã start stack với `--profile producer`, thì service `stock-producer` đã chạy.

Tuy nhiên để demo dễ kiểm soát hơn, nên chạy one-shot ở `Terminal 2`:

```powershell
python scripts/publish_stock_ticks.py --bootstrap-servers localhost:29092 --source auto --max-iterations 1
```

Nếu không có internet nhưng đã có `data/raw/*.csv`:

```powershell
python scripts/publish_stock_ticks.py --bootstrap-servers localhost:29092 --source csv --max-iterations 1
```

## 10. Airflow: nên chạy DAG nào?

Có 2 kiểu chạy:

- `kiểm thử từng phần`
- `chạy luồng hoàn chỉnh Kafka -> inference`

### 10.1. Kiểm thử từng phần

Trigger theo thứ tự:

1. `ie212_kafka_end_to_end_smoke_test`
2. `ie212_spark_exec_pipeline`
3. `ie212_data_pipeline`

Ý nghĩa:

- DAG 1 chứng minh Kafka ghi được vào `stock.kafka_ticks_batch`
- DAG 2 ghi parquet, upload MinIO và ghi audit
- DAG 3 validate batch path

### 10.2. Luồng hoàn chỉnh Kafka -> model -> dashboard

DAG chính hiện tại là:

- `ie212_kafka_to_inference_pipeline`

DAG này sẽ tự chạy:

1. publish một vòng vào Kafka
2. Spark batch ghi `stock.kafka_ticks_batch`
3. Spark ghi parquet
4. đồng bộ parquet lên MinIO
5. build bundle inference từ parquet trong MinIO
6. chạy checkpoint inference
7. lưu prediction vào `stock.inference_predictions`
8. validate đầu ra

Nếu DAG này chạy xanh, bạn có thể nói rằng:

- Kafka đã tham gia vào pipeline Big Data
- MinIO đã tham gia trực tiếp vào inference path
- dữ liệu từ Kafka đã đi vào model
- prediction cuối cùng đã phụ thuộc vào Kafka

Sau khi DAG này chạy xong, mở:

- Dashboard: [http://localhost:8008/dashboard](http://localhost:8008/dashboard)
- API docs: [http://localhost:8008/docs](http://localhost:8008/docs)

Kết quả mong đợi:

- dashboard hiển thị `latest run`
- có dữ liệu trong bảng prediction
- API không còn báo `HTTP 500`

## 11. Nếu dashboard mở được nhưng không có dữ liệu

Nếu giao diện dashboard mở được nhưng báo:

- `API Unhealthy`
- `HTTP 500`
- không tải được `latest run` hoặc `recent runs`

thì nguyên nhân thường là `stock.inference_predictions` chưa có dữ liệu.

Cách xử lý đúng là chạy:

- `ie212_kafka_to_inference_pipeline`

vì DAG này sẽ tự tạo prediction mới và lưu vào PostgreSQL.

## 12. Reset workspace

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

## 13. Ghi chú nhanh

- PostgreSQL host port là `15432`
- Kafka host port là `29092`
- nếu không có internet thì producer nên dùng `--source csv`
- nếu `data/raw/*.csv` chưa có thì hãy chạy `python scripts/run_train.py` trước
- DAG demo hoàn chỉnh hiện tại là `ie212_kafka_to_inference_pipeline`
