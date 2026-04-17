# IE212 - Hướng dẫn chạy hệ thống

README này chỉ tập trung vào một mục tiêu: `chạy hệ thống theo đúng thứ tự, ít nhầm lẫn nhất`.

## 1. Hệ thống gồm những gì?

Luồng chính của project là:

```text
yfinance hoặc data/raw CSV
-> stock-producer
-> Kafka topic stock-price
-> Spark
-> PostgreSQL / parquet
-> MinIO / Airflow validation
-> FastAPI dashboard
```

Ý nghĩa của Kafka trong project:

- Kafka là `lớp nhận dữ liệu đầu vào`
- producer đẩy giá cổ phiếu vào topic `stock-price`
- Spark đọc lại từ Kafka để xử lý
- vì vậy Kafka không phải phần phụ, mà là mắt xích ở giữa pipeline Big Data

## 2. Cần mở gì trước khi chạy?

Bạn nên mở:

- `Terminal 1`: để chạy Docker stack
- `Terminal 2`: để chạy lệnh local như train, producer, save inference
- `Browser`: để mở Airflow / dashboard / docs

Làm theo cách này sẽ dễ quan sát nhất.

## 3. Chuẩn bị môi trường

### 3.1. Clone và cài Python dependencies

Chạy ở `Terminal 1` hoặc `Terminal 2` đều được:

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

Phần này nên chạy trước để có:

- `data/raw/*.csv`
- checkpoint model
- inference JSON

Chạy ở `Terminal 2`:

### 4.1. Tải dữ liệu raw

```powershell
python scripts/run_train.py
```

Muốn tải lại toàn bộ:

```powershell
python scripts/run_train.py --refresh
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

Nếu bạn muốn chạy luôn cả producer trong Docker:

```powershell
docker compose --env-file compose/.env -f compose/compose.yaml --profile producer up -d --build
```

Nếu bạn chưa muốn chạy producer Docker:

```powershell
docker compose --env-file compose/.env -f compose/compose.yaml up -d --build
```

## 6. Mở các địa chỉ cần thiết

Mở ở `Browser`:

- Airflow UI: [http://localhost:8088](http://localhost:8088)
- FastAPI docs: [http://localhost:8008/docs](http://localhost:8008/docs)
- Dashboard: [http://localhost:8008/dashboard](http://localhost:8008/dashboard)
- Spark Master UI: [http://localhost:8080](http://localhost:8080)
- Spark Worker UI: [http://localhost:8081](http://localhost:8081)
- MinIO Console: [http://localhost:9001](http://localhost:9001)

### Đăng nhập Airflow

Airflow có yêu cầu tài khoản.

Theo [compose/.env.example](compose/.env.example), mặc định là:

- username: `airflow`
- password: `airflow`

Nếu bạn đã sửa `compose/.env` thì dùng thông tin trong file đó.

## 7. Kafka: bạn thật sự cần chạy lệnh nào?

Đây là phần dễ nhầm nhất, nên đọc kỹ:

### Trường hợp A - Bạn đã start Docker với `--profile producer`

Khi đó `stock-producer` đã chạy trong Docker rồi.

Nghĩa là:

- `không bắt buộc` chạy thêm producer local
- nhưng nếu muốn demo rõ ràng từng bước, bạn vẫn có thể chạy local producer one-shot ở `Terminal 2`

Lệnh one-shot:

```powershell
python scripts/publish_stock_ticks.py --bootstrap-servers localhost:29092 --source auto --max-iterations 1
```

Nếu không có internet nhưng đã có `data/raw/*.csv`:

```powershell
python scripts/publish_stock_ticks.py --bootstrap-servers localhost:29092 --source csv --max-iterations 1
```

### Trường hợp B - Bạn start Docker không có `--profile producer`

Khi đó `stock-producer` chưa chạy.

Bạn phải chọn một trong hai cách:

#### Cách 1. Chạy producer local ở `Terminal 2`

```powershell
python scripts/publish_stock_ticks.py --bootstrap-servers localhost:29092 --source auto --max-iterations 1
```

#### Cách 2. Bật riêng producer Docker

```powershell
docker compose --env-file compose/.env -f compose/compose.yaml --profile producer up -d stock-producer
```

### Kết luận ngắn gọn

Nếu bạn muốn ít rối nhất, hãy dùng đúng 1 cách sau:

- `Cách đơn giản nhất`: start Docker với `--profile producer`, rồi không cần chạy thêm producer local
- `Cách dễ demo nhất`: vẫn start với `--profile producer`, nhưng chạy thêm `--max-iterations 1` để nhìn rõ một lượt message vào Kafka

## 8. Airflow: bấm gì, ở đâu?

Sau khi Kafka đã có dữ liệu, vào Airflow:

1. Mở [http://localhost:8088](http://localhost:8088)
2. Đăng nhập bằng:
   - username `airflow`
   - password `airflow`
3. Tìm DAG `ie212_kafka_end_to_end_smoke_test`
4. Nếu DAG đang `Paused`, bật công tắc sang `On`
5. Bấm vào tên DAG
6. Ở góc trên bên phải, bấm `Trigger DAG`
7. Chờ DAG chạy xong

### DAG này làm gì?

`ie212_kafka_end_to_end_smoke_test` sẽ:

1. gọi producer one-shot
2. gọi Spark batch đọc Kafka
3. ghi dữ liệu vào `stock.kafka_ticks_batch`
4. validate bảng đó trong PostgreSQL

Nếu DAG chạy `success`, nghĩa là Kafka đã thực sự tham gia pipeline.

## 9. Nên chạy DAG nào?

Nếu mục tiêu là chứng minh Kafka có vai trò trong hệ thống, hãy ưu tiên theo thứ tự này:

1. `ie212_kafka_end_to_end_smoke_test`
2. `ie212_spark_exec_pipeline`
3. `ie212_data_pipeline`

Ý nghĩa:

- `ie212_kafka_end_to_end_smoke_test`
  - test Kafka -> Spark -> PostgreSQL nhanh nhất
- `ie212_spark_exec_pipeline`
  - chạy batch Spark -> PostgreSQL + parquet -> MinIO
- `ie212_data_pipeline`
  - kiểm tra Kafka / Spark / MinIO / PostgreSQL đang ổn hay không

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
2. đăng nhập `airflow / airflow`
3. trigger DAG `ie212_kafka_end_to_end_smoke_test`
4. mở [http://localhost:8008/dashboard](http://localhost:8008/dashboard)

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
