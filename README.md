# IE212 - Stock Price Prediction

Project này là notebook dự báo giá cổ phiếu cho môn IE212, xây dựng pipeline từ tải dữ liệu đến huấn luyện và so sánh mô hình. Toàn bộ quy trình được thực hiện trong `Stock_prediction_v2_patched.ipynb`.

## Tổng quan

Notebook triển khai bài toán dự báo giá đóng cửa cổ phiếu từ dữ liệu Yahoo Finance và so sánh 5 mô hình:

- Linear Regression
- DNN
- CNN
- LSTM
- Hybrid LSTM-GCN

Pipeline chính gồm:

- Tải dữ liệu lịch sử cho 10 mã cổ phiếu bằng `yfinance`
- Làm sạch và đồng bộ `common trading dates`
- Tạo đặc trưng như `Close`, `MA20` và scale bằng `MinMaxScaler`
- Xây dựng đồ thị quan hệ giữa các cổ phiếu bằng Pearson correlation + Apriori
- Huấn luyện và đánh giá bằng expanding window backtest
- Tổng hợp chỉ số `MSE`, `RMSE`, `MAE`, vẽ biểu đồ và lưu kết quả ra file CSV

Mặc định notebook đang sử dụng tập ticker:

`AAPL`, `MSFT`, `CMCSA`, `COST`, `QCOM`, `ADBE`, `SBUX`, `INTU`, `AMD`, `INTC`

Khoảng thời gian dữ liệu mặc định:

- Bắt đầu: `2005-01-01`
- Kết thúc: `2023-12-31`

## Cấu trúc project

- `Stock_prediction_v2_patched.ipynb`: notebook chính chứa toàn bộ pipeline, model và phần thực nghiệm
- `requirements.txt`: danh sách thư viện cần cài đặt
- `README.md`: hướng dẫn tổng quan và cách chạy project

## Cách cài đặt thư viện

Yêu cầu:

- Python 3.10 trở lên
- Khuyến nghị dùng môi trường ảo (`venv`)

Tạo môi trường ảo và cài đặt thư viện:

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Nếu bạn chạy bằng Jupyter hoặc VS Code Notebook, hãy chọn kernel từ môi trường `.venv` sau khi cài đặt xong.

## Cách chạy project

Project này được chạy chủ yếu qua notebook.

### Cách 1: Chạy bằng Jupyter Notebook

```bash
jupyter notebook
```

Sau đó mở file `Stock_prediction_v2_patched.ipynb` và chạy lần lượt từng cell từ trên xuống dưới.

### Cách 2: Chạy bằng VS Code

- Mở thư mục project trong VS Code
- Mở file `Stock_prediction_v2_patched.ipynb`
- Chọn đúng Python interpreter / kernel của `.venv`
- Bấm `Run All` hoặc chạy từng cell theo thứ tự

## Đầu ra sau khi chạy

Sau khi chạy xong notebook, project sẽ:

- Hiển thị bảng so sánh kết quả giữa các mô hình và các giá trị lookback `11` và `21`
- Vẽ biểu đồ dự báo so với giá trị thực tế
- Lưu 2 file kết quả:
  - `summary_all_models.csv`
  - `all_results_all_models.csv`

## Ghi chú

- Notebook có sử dụng `torch`, nếu máy có GPU và cấu hình phù hợp thì sẽ tự động dùng `cuda`
- Thời gian chạy có thể khá lâu vì notebook huấn luyện nhiều mô hình và backtest trên nhiều bước thời gian
- Cần kết nối Internet để tải dữ liệu từ Yahoo Finance
