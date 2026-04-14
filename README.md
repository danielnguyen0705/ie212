# IE212 - Stock Price Prediction

Project này phục vụ bài toán dự báo giá cổ phiếu cho môn `IE212`. Toàn bộ quy trình chính hiện được triển khai trong notebook `Stock_prediction_v2_patched.ipynb`.

README này tập trung vào việc hướng dẫn cài môi trường local để chạy file notebook `.ipynb` bằng `VS Code + virtual environment (.venv)`.

## Tổng quan project

Notebook hiện bao gồm các bước chính:

- Tải dữ liệu lịch sử cổ phiếu từ `Yahoo Finance`
- Làm sạch và đồng bộ dữ liệu theo `common trading dates`
- Tạo đặc trưng đầu vào và chuẩn hóa dữ liệu
- Huấn luyện, đánh giá và so sánh nhiều mô hình dự báo
- Xuất kết quả và biểu đồ phục vụ thực nghiệm

File chính trong project:

- `Stock_prediction_v2_patched.ipynb`: notebook chính
- `requirements.txt`: danh sách thư viện cần cài
- `README.md`: hướng dẫn cài đặt và chạy project

## 1. Yêu cầu trước khi bắt đầu

Máy cần có sẵn:

- `Python 3.10` hoặc `Python 3.11`
- `VS Code`
- Extension `Python` trong VS Code
- Extension `Jupyter` trong VS Code
- `Git`

Khuyến nghị:

- Nên dùng `Python 3.10` hoặc `3.11` để hạn chế lỗi tương thích thư viện
- Không nên cài trực tiếp thư viện vào Python hệ thống
- Nên dùng môi trường ảo `.venv` cho project

## 2. Clone project

```bash
git clone <link-repository>
cd ie212
```

## 3. Tạo virtual environment

Trong terminal tại thư mục project, chạy:

```bash
python -m venv .venv
```

Sau khi hoàn tất, thư mục `.venv/` sẽ được tạo trong project.

## 4. Kích hoạt virtual environment

Nếu dùng `PowerShell` trên Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Nếu bị chặn quyền chạy script, chạy trước:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Sau đó kích hoạt lại:

```powershell
.venv\Scripts\Activate.ps1
```

Khi kích hoạt thành công, terminal sẽ hiển thị tiền tố tương tự:

```powershell
(.venv) PS D:\ie212>
```

## 5. Cài thư viện từ `requirements.txt`

Nên nâng cấp `pip` trước:

```bash
python -m pip install --upgrade pip
```

Sau đó cài toàn bộ thư viện:

```bash
pip install -r requirements.txt
```

## 6. Đăng ký kernel cho Jupyter / VS Code

Sau khi đã activate `.venv`, chạy:

```bash
python -m ipykernel install --user --name stockv9 --display-name "Python (.venv) stockv9"
```

Nếu xuất hiện thông báo dạng sau thì là thành công:

```text
Installed kernelspec stockv9 in ...
```

## 7. Mở notebook trong VS Code

Thực hiện lần lượt:

1. Mở file notebook `.ipynb`
2. Ở góc trên bên phải, chọn `Kernel`
3. Chọn kernel `Python (.venv) stockv9`

Nếu chưa thấy kernel này:

1. Chọn `Select Another Kernel`
2. Tìm `stockv9`

## 8. Kiểm tra notebook đã dùng đúng môi trường chưa

Chạy cell sau trong notebook:

```python
import sys
print(sys.executable)
```

Nếu đúng môi trường, kết quả sẽ gần giống:

```text
D:\ie212\.venv\Scripts\python.exe
```

Tiếp theo có thể kiểm tra import thư viện:

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

Nếu không báo lỗi thì môi trường đã sẵn sàng.

## 9. `requirements.txt`

Project hiện cài đặt thư viện thông qua file `requirements.txt`.

Ví dụ nội dung có thể bao gồm:

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

Cài bằng lệnh:

```bash
pip install -r requirements.txt
```

## 10. `.gitignore`

Project nên có `.gitignore` để tránh đẩy file môi trường và file tạm lên Git.

Các mục nên ignore:

```gitignore
.venv/
__pycache__/
.ipynb_checkpoints/
.vscode/
```

Có thể mở rộng thêm để bỏ qua dữ liệu tạm, model artifacts, log, hoặc các file sinh ra trong quá trình thử nghiệm.

## 11. Nếu kernel không hiện trong VS Code

Thử lần lượt các cách sau:

### Cách 1: Reload VS Code

1. Nhấn `Ctrl + Shift + P`
2. Gõ `Developer: Reload Window`

### Cách 2: Chọn lại interpreter

1. Nhấn `Ctrl + Shift + P`
2. Gõ `Python: Select Interpreter`
3. Chọn:

```text
D:\ie212\.venv\Scripts\python.exe
```

### Cách 3: Đóng rồi mở lại notebook

Sau đó chọn lại kernel `stockv9`.

## 12. Các bước setup ngắn gọn

Nếu đã quen, có thể setup nhanh bằng các lệnh sau:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m ipykernel install --user --name stockv9 --display-name "Python (.venv) stockv9"
```

Sau đó mở notebook trong VS Code và chọn kernel `Python (.venv) stockv9`.

## 13. Trạng thái hiện tại

README này hiện mới mô tả các nội dung:

- Tạo virtual environment
- Cài thư viện bằng `requirements.txt`
- Đăng ký kernel Jupyter
- Chạy notebook trong VS Code

Các phần như `Docker`, `Kafka`, `Spark`, `Airflow`, `PostgreSQL`, `MinIO`, `FastAPI` sẽ được bổ sung sau.
