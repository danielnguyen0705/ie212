# IE212 - Stock Price Prediction Project

Project này là quá trình hiện thực hóa mô hình dự đoán giá cổ phiếu từ notebook nghiên cứu sang một project local có cấu trúc rõ ràng, sẵn sàng để tiếp tục tích hợp vào hệ thống Big Data ở giai đoạn sau.

Hiện tại project đã đi qua 2 mốc chính:

- Setup môi trường local để chạy notebook `.ipynb` bằng `VS Code + .venv`
- Tách các thành phần cốt lõi từ notebook sang code Python có cấu trúc trong `src/` và `scripts/`

## 1. Trạng thái hiện tại của project

### 1.1. Cài đặt môi trường local thành công

Project đã setup và chạy được môi trường local với:

- Virtual environment `.venv`
- Cài thư viện bằng `requirements.txt`
- Đăng ký Jupyter kernel cho VS Code
- Mở và chạy notebook `.ipynb` trực tiếp trong VS Code

### 1.2. Chạy notebook gốc thành công

Notebook gốc hiện nằm tại:

- `notebooks/stock-predictionv9.ipynb`

Notebook này đã được dùng như nguồn logic gốc để:

- Đối chiếu kết quả
- Kiểm tra lại pipeline ban đầu
- Làm mốc tham chiếu khi tách code sang project Python local

### 1.3. Đã tách notebook thành project Python local

Các phần cốt lõi đã được tách ra khỏi notebook và đưa vào thư mục `src/`:

- `src/config.py`: chứa cấu hình chính của project
- `src/data_loader.py`: tải dữ liệu từ `yfinance`, làm sạch dữ liệu và align ngày giao dịch chung
- `src/features.py`: xây dựng tensor đặc trưng như `features_3d`, `close_2d`, `return_2d`
- `src/dataset.py`: định nghĩa `StockGraphDataset`
- `src/models.py`: chứa `SimpleGCNLayer`, `LSTMOnlyModel`, `HybridLSTMGNNGraphGate`
- `src/graph_builder.py`: xây graph từ Pearson correlation, association-style relation và graph kết hợp đã normalize
- `src/expanding.py`: xử lý leakage-safe scaling, sample building và prepare expanding step data
- `src/train_eval.py`: train loop, eval loop, predict helpers và compute metrics
- `src/artifacts.py`: các hàm hỗ trợ lưu và load checkpoint, JSON metadata

### 1.4. Đã tạo các script chạy ngoài notebook

Project hiện có thể chạy nhiều bước bằng script thay vì phụ thuộc hoàn toàn vào notebook:

- `scripts/run_train.py`: test load data và feature tensor
- `scripts/test_model_forward.py`: test forward pass của model
- `scripts/test_expanding_data.py`: test scaling và sample building
- `scripts/test_graph_builder.py`: test graph builder
- `scripts/test_prepare_step.py`: test prepare expanding step
- `scripts/run_experiment.py`: chạy experiment ngoài notebook
- `scripts/test_load_checkpoint.py`: test load lại checkpoint model

## 2. Kết quả đã đạt được

### 2.1. Dữ liệu đã được tải và lưu local

Dữ liệu raw hiện được lưu trong:

```text
data/raw/
```

Mỗi mã cổ phiếu được lưu thành một file `.csv` riêng.

### 2.2. Experiment đã chạy được ngoài notebook

Experiment expanding window được chạy bằng lệnh:

```bash
python -m scripts.run_experiment
```

Luồng chạy hiện tại hỗ trợ:

- `Linear Regression` baseline
- `LSTM` expanding baseline
- `Hybrid LSTM-GNN Graph-Gated`
- Tạo bảng kết quả tổng hợp
- Tạo bảng so sánh theo từng ngày test
- Tạo bảng MSE theo từng mã cổ phiếu

### 2.3. Output thực nghiệm đã được lưu ra file

Các file output hiện có trong thư mục `outputs/`:

- `outputs/exp_results_full.csv`
- `outputs/compare_step_full.csv`
- `outputs/stock_mse_full.csv`
- `outputs/graph_step_full.csv`
- `outputs/gate_step_full.csv`
- `outputs/metrics_full.json`

### 2.4. Hỗ trợ lưu và load model artifact

Project đã có cơ chế lưu artifact thông qua `src/artifacts.py`.

Khi chạy:

```bash
python -m scripts.run_experiment
```

script sẽ lưu các artifact sau vào thư mục `models/`:

- `models/lstm_expanding_best_full.pt`
- `models/hybrid_expanding_best_full.pt`
- `models/run_metadata_full.json`

Sau đó có thể kiểm tra khả năng load lại checkpoint bằng:

```bash
python -m scripts.test_load_checkpoint
```

Điều này cho phép project quản lý được:

- Model checkpoint
- Train config
- Metrics đi kèm
- Metadata của lần chạy

## 3. Cấu trúc thư mục hiện tại

```text
IE212/
├── .venv/
├── .gitignore
├── README.md
├── requirements.txt
├── notebooks/
│   └── stock-predictionv9.ipynb
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── data_loader.py
│   ├── features.py
│   ├── dataset.py
│   ├── models.py
│   ├── graph_builder.py
│   ├── expanding.py
│   ├── train_eval.py
│   └── artifacts.py
├── scripts/
│   ├── __init__.py
│   ├── run_train.py
│   ├── run_experiment.py
│   ├── test_model_forward.py
│   ├── test_expanding_data.py
│   ├── test_graph_builder.py
│   ├── test_prepare_step.py
│   └── test_load_checkpoint.py
├── data/
│   ├── raw/
│   └── processed/
├── models/
└── outputs/
```

Trong workspace hiện tại, `models/` đã có các file checkpoint và metadata được sinh ra từ lần chạy experiment gần nhất.

## 4. Hướng dẫn cài môi trường local để chạy notebook trên VS Code

README này vẫn giữ phần setup notebook vì đây là bước nền tảng để tái lập môi trường local và đối chiếu kết quả với notebook gốc.

### 4.1. Yêu cầu trước khi bắt đầu

Máy cần có sẵn:

- `Python 3.10` hoặc `Python 3.11`
- `VS Code`
- Extension `Python` trong VS Code
- Extension `Jupyter` trong VS Code
- `Git`

Khuyến nghị:

- Dùng `Python 3.10` hoặc `3.11` để tránh lỗi tương thích thư viện
- Không nên cài trực tiếp thư viện vào Python hệ thống
- Nên dùng `.venv` cho project

### 4.2. Clone project

```bash
git clone <link-repository>
cd ie212
```

### 4.3. Tạo virtual environment

```bash
python -m venv .venv
```

Sau khi hoàn tất, thư mục `.venv/` sẽ xuất hiện trong project.

### 4.4. Kích hoạt virtual environment

Nếu dùng `PowerShell` trên Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Nếu bị chặn quyền chạy script, chạy trước:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Sau đó chạy lại:

```powershell
.venv\Scripts\Activate.ps1
```

Khi thành công, terminal sẽ có tiền tố tương tự:

```powershell
(.venv) PS D:\ie212>
```

### 4.5. Cài thư viện từ `requirements.txt`

Nâng cấp `pip` trước:

```bash
python -m pip install --upgrade pip
```

Sau đó cài thư viện:

```bash
pip install -r requirements.txt
```

Nội dung `requirements.txt` hiện tại:

```text
numpy>=1.26
pandas>=2.2
matplotlib>=3.8
scikit-learn>=1.4
yfinance>=0.2.54
mlxtend>=0.23
torch>=2.2
jupyter>=1.0
ipykernel>=6.29
```

### 4.6. Đăng ký kernel cho Jupyter / VS Code

Sau khi đã activate `.venv`, chạy:

```bash
python -m ipykernel install --user --name stockv9 --display-name "Python (.venv) stockv9"
```

Nếu xuất hiện dòng tương tự sau thì là thành công:

```text
Installed kernelspec stockv9 in ...
```

### 4.7. Mở notebook trong VS Code

Thực hiện lần lượt:

1. Mở file `notebooks/stock-predictionv9.ipynb`
2. Ở góc trên bên phải, chọn `Kernel`
3. Chọn `Python (.venv) stockv9`

Nếu chưa thấy:

1. Chọn `Select Another Kernel`
2. Tìm `stockv9`

### 4.8. Kiểm tra notebook đã dùng đúng môi trường chưa

Chạy cell sau:

```python
import sys
print(sys.executable)
```

Nếu đúng môi trường, kết quả sẽ gần giống:

```text
D:\ie212\.venv\Scripts\python.exe
```

Có thể test import nhanh bằng cell sau:

```python
import numpy as np
import pandas as pd
import matplotlib
import sklearn
import torch
import yfinance as yf

print("All imports OK")
print("Torch version:", torch.__version__)
```

Nếu không có lỗi thì môi trường đã sẵn sàng.

### 4.9. Nếu kernel không hiện trong VS Code

Thử lần lượt các cách sau:

1. Reload VS Code bằng `Developer: Reload Window`
2. Chọn lại interpreter bằng `Python: Select Interpreter`
3. Trỏ lại đúng interpreter của `.venv`:

```text
D:\ie212\.venv\Scripts\python.exe
```

4. Đóng rồi mở lại notebook, sau đó chọn lại kernel `stockv9`

## 5. Cách chạy project hiện tại

### 5.1. Kích hoạt môi trường

```powershell
.venv\Scripts\Activate.ps1
```

### 5.2. Chạy experiment chính

```bash
python -m scripts.run_experiment
```

### 5.3. Test load checkpoint

```bash
python -m scripts.test_load_checkpoint
```

## 6. Ý nghĩa của mốc hiện tại

Project hiện đã vượt qua giai đoạn notebook nghiên cứu ban đầu và tiến tới mức:

- Code có cấu trúc rõ ràng
- Experiment chạy được bằng script
- Kết quả được lưu ra file
- Model có thể lưu checkpoint và load lại

Đây là mốc quan trọng trước khi chuyển sang giai đoạn tích hợp vào kiến trúc Big Data.

## 7. Bước tiếp theo

Sau khi hoàn thành local ML project và artifact management, các bước tiếp theo dự kiến là:

- Tạo thư mục `compose/`
- Dựng `Docker Compose`
- Dựng `PostgreSQL`
- Dựng `MinIO`
- Sau đó tiếp tục với `Kafka`, `Spark`, `Airflow`, `FastAPI`

## 8. Ghi chú

Notebook gốc vẫn được giữ trong `notebooks/` để:

- Đối chiếu logic
- Kiểm tra lại kết quả
- Dùng làm nguồn tham chiếu khi cần

Tuy nhiên, hướng phát triển chính từ thời điểm này là ưu tiên:

- Chạy bằng script trong `scripts/`
- Tái sử dụng code trong `src/`

## 9. Tóm tắt ngắn

Project hiện đã làm được:

- Setup môi trường local thành công
- Chạy notebook trong VS Code thành công
- Tách logic chính khỏi notebook
- Chạy experiment bằng script
- Lưu output thực nghiệm
- Hỗ trợ lưu checkpoint model
- Hỗ trợ load checkpoint lại

Mốc tiếp theo là triển khai hạ tầng Big Data để đưa model vào hệ thống hoàn chỉnh.
