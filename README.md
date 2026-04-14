# IE212 - Stock Price Prediction with Local ML Pipeline and Big Data Roadmap

## 1. Giới thiệu

Đây là project môn `IE212 - Công nghệ dữ liệu lớn`, xuất phát từ bài toán dự đoán giá cổ phiếu dựa trên mô hình lai giữa `LSTM` và `GNN`, đồng thời có thêm phần cải tiến ở local ML phase.

Project hiện được triển khai theo 2 giai đoạn chính:

- `Giai đoạn 1 - Local ML Project`
  - Chạy notebook gốc
  - Tách code từ notebook thành project Python có cấu trúc
  - Chạy experiment ngoài notebook
  - Lưu checkpoint và model artifact
  - Kiểm tra load lại checkpoint
- `Giai đoạn 2 - Big Data System`
  - Dựng hạ tầng bằng `Docker Compose`
  - Bắt đầu từ storage layer với `PostgreSQL` và `MinIO`
  - Các bước tiếp theo sẽ là `Kafka`, `Spark`, `Airflow`, `FastAPI` và tích hợp model vào pipeline Big Data

## 2. Trạng thái hiện tại

### Đã hoàn thành

#### Local ML phase

- Tạo môi trường `.venv`
- Cài dependencies qua `requirements.txt`
- Chạy notebook thành công trong VS Code
- Tách code khỏi notebook thành các module trong `src/`
- Tạo các script trong `scripts/`
- Chạy experiment ngoài notebook
- Lưu checkpoint model
- Load lại checkpoint thành công

#### Big Data phase

- Tạo thư mục `compose/`
- Dựng thành công `PostgreSQL`
- Dựng thành công `MinIO`
- PostgreSQL đã được khởi tạo:
  - schema `stock`
  - bảng `stock.predictions`
  - bảng `stock.model_registry`
- MinIO đã được khởi tạo bucket:
  - `raw`
  - `processed`
  - `models`
  - `artifacts`

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
├── data/
│   ├── processed/
│   └── raw/
├── models/
├── notebooks/
│   └── stock-predictionv9.ipynb
├── outputs/
├── scripts/
│   ├── __init__.py
│   ├── run_experiment.py
│   ├── run_train.py
│   ├── test_expanding_data.py
│   ├── test_graph_builder.py
│   ├── test_load_checkpoint.py
│   ├── test_model_forward.py
│   └── test_prepare_step.py
├── src/
│   ├── __init__.py
│   ├── artifacts.py
│   ├── config.py
│   ├── data_loader.py
│   ├── dataset.py
│   ├── expanding.py
│   ├── features.py
│   ├── graph_builder.py
│   ├── models.py
│   └── train_eval.py
├── .gitignore
├── README.md
└── requirements.txt
```

## 4. Ý nghĩa các thư mục chính

- `src/`: mã nguồn chính sau khi tách khỏi notebook
- `scripts/`: các script test, train và evaluate
- `notebooks/`: notebook nghiên cứu gốc
- `data/`: dữ liệu raw và processed
- `outputs/`: kết quả thực nghiệm
- `models/`: checkpoint model và metadata
- `compose/`: cấu hình Docker Compose cho Big Data services
- `compose/postgres/init/001_init.sql`: SQL khởi tạo schema và bảng ban đầu cho PostgreSQL

## 5. Các lệnh local ML đã dùng

### Kích hoạt môi trường ảo trên Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

### Chạy các script kiểm tra và thực nghiệm

```bash
python -m scripts.run_train
python -m scripts.test_model_forward
python -m scripts.test_expanding_data
python -m scripts.test_graph_builder
python -m scripts.test_prepare_step
python -m scripts.run_experiment
python -m scripts.test_load_checkpoint
```

### Ý nghĩa nhanh của từng script

- `run_train`: load dữ liệu và chạy pipeline train cơ bản
- `test_model_forward`: kiểm tra forward pass của model
- `test_expanding_data`: kiểm tra expanding window data preparation
- `test_graph_builder`: kiểm tra graph construction
- `test_prepare_step`: kiểm tra dữ liệu train, val, test cho từng expanding step
- `run_experiment`: chạy thực nghiệm ngoài notebook
- `test_load_checkpoint`: kiểm tra load lại checkpoint đã lưu

## 6. Big Data phase - Storage layer đầu tiên

Hiện tại project đã dựng thành công 2 service đầu tiên bằng Docker Compose:

- `PostgreSQL`: dùng để lưu metadata, prediction results và model registry
- `MinIO`: dùng làm object storage kiểu S3 cho raw data, processed data, models và artifacts

Ngoài 2 service chính, `compose.yaml` còn có `minio-bootstrap` để tự động tạo bucket cần thiết khi khởi động hệ thống.

## 7. Cấu hình Docker Compose hiện tại

Các file liên quan:

- `compose/compose.yaml`
- `compose/.env`
- `compose/postgres/init/001_init.sql`

### Service hiện có

- `ie212-postgres`
- `ie212-minio`

### Bucket MinIO đã có

- `raw`
- `processed`
- `models`
- `artifacts`

## 8. Cách chạy PostgreSQL và MinIO

### Bước 1: đi vào thư mục `compose`

```bash
cd compose
```

### Bước 2: khởi động container

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

Kết quả mong đợi:

- schema `stock`
- bảng `stock.predictions`
- bảng `stock.model_registry`

## 10. Các lệnh kiểm tra MinIO

### Health check

```bash
curl.exe -i http://localhost:9000/minio/health/live
```

### Mở giao diện web

Truy cập trình duyệt tại:

```text
http://localhost:9001
```

Thông tin đăng nhập hiện tại được cấu hình trong file:

```text
compose/.env
```

Giá trị hiện tại trong repo:

```text
user: minioadmin
password: change_me_minio
```

Nên đổi password mặc định trước khi dùng lâu dài.

## 11. Các lệnh quản lý Docker Compose

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

### Tắt hệ thống

```bash
docker compose down
```

### Tắt và xóa luôn volume dữ liệu

```bash
docker compose down -v
```

`Cẩn thận:` `down -v` sẽ xóa dữ liệu PostgreSQL và MinIO local.

## 12. Những gì đã xác nhận thành công

### Local ML

- Notebook chạy được
- Code sau khi tách vẫn chạy ổn
- Experiment chạy ngoài notebook thành công
- Checkpoint model đã lưu thành công
- Checkpoint đã load lại thành công

### Big Data storage

- PostgreSQL container chạy healthy
- Schema `stock` đã được tạo
- Bảng `predictions` và `model_registry` đã được tạo
- MinIO web UI truy cập được
- Bucket `raw`, `processed`, `models`, `artifacts` đã được tạo

## 13. Bước tiếp theo

Sau storage layer, roadmap tiếp theo của project là:

- Dựng `Kafka` bằng Docker Compose
- Tạo producer và consumer test
- Dựng `Spark` để xử lý dữ liệu
- Dựng `Airflow` để orchestration pipeline
- Dựng `FastAPI` để serving model
- Tích hợp model local hiện tại vào hệ thống Big Data

## 14. Ghi chú

- Hiện tại project đang chạy tốt ở phase local ML
- Big Data phase mới hoàn thành bước đầu là storage layer
- Đây là điểm checkpoint phù hợp trước khi sang Kafka
- Notebook gốc vẫn được giữ trong `notebooks/` để đối chiếu logic và kết quả khi cần
- Hướng phát triển chính từ thời điểm này là ưu tiên chạy bằng script trong `scripts/` và tái sử dụng code trong `src/`

## 15. Quick Start ngắn gọn

### Local ML

```powershell
.\.venv\Scripts\Activate.ps1
python -m scripts.run_experiment
python -m scripts.test_load_checkpoint
```

### Big Data storage

```bash
cd compose
docker compose up -d
docker compose ps
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "\dn"
docker exec -it ie212-postgres psql -U stock_user -d stock_project -c "\dt stock.*"
curl.exe -i http://localhost:9000/minio/health/live
```

### MinIO UI

```text
http://localhost:9001
```

## 16. Tác giả / mục đích

Project phục vụ các mục tiêu:

- Nghiên cứu và tái hiện bài toán dự đoán giá cổ phiếu
- Cải tiến mô hình local ML
- Triển khai pipeline Big Data end-to-end cho đồ án môn IE212
