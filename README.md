# IE212 - Xây dựng hệ thống dự đoán giá cổ phiếu sử dụng mô hình kết hợp LSTM và Graph Neural Network trên kiến trúc Big Data

**Sơ đồ kiến trúc hệ thống**

![Sơ đồ kiến trúc hệ thống](img/system_architecture.png)

## 1. Cần mở gì trước khi chạy?

- `Terminal 1`: chạy Docker stack
- `Terminal 2`: chạy lệnh local
- `Browser`: mở Airflow, dashboard, docs

## 2. Chuẩn bị môi trường

### 2.1. Clone và cài Python dependencies

```powershell
git clone <repo-url>
cd ie212

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2.2. Tạo file env cho Docker

```powershell
Copy-Item compose\.env.example compose\.env
```

## 3. Chuẩn bị dữ liệu và model local

Chạy ở `Terminal 2`:

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/run_train.py
python scripts/run_experiment.py
```

Kết quả mong đợi:

- có `data/raw/*.csv`
- có checkpoint trong `models/`

## 4. Khởi động Big Data stack

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

## 5. Các địa chỉ cần mở

- Airflow UI: [http://localhost:8088](http://localhost:8088)
- FastAPI docs: [http://localhost:8008/docs](http://localhost:8008/docs)
- Dashboard: [http://localhost:8008/dashboard](http://localhost:8008/dashboard)
- Spark Master UI: [http://localhost:8080](http://localhost:8080)
- Spark Worker UI: [http://localhost:8081](http://localhost:8081)
- MinIO Console: [http://localhost:9001](http://localhost:9001)

## 6. Đăng nhập Airflow

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

## 7. Chạy DAG hoàn chỉnh:

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

## 8. Mở frontend:

```powershell
cd D:\ie212\frontend
npm install
npm run dev
```
Sau đó mở vào trình duyệt: [http://localhost:5173](http://localhost:5173)

## 9. Reset workspace 

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
