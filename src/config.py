# src/config.py
# ============================================================================
# CẤU HÌNH TRUNG TÂM CỦA TOÀN BỘ HỆ THỐNG DỰ ĐOÁN GIÁ CỔ PHIẾU
# Dự án: Ứng dụng kiến trúc Dữ liệu lớn + Hybrid LSTM-GNN
# ============================================================================

# --------------------------------------------------------------------------
# DANH SÁCH MÃ CỔ PHIẾU THEO DÕI (10 mã NASDAQ đại diện đa ngành)
# --------------------------------------------------------------------------
TICKERS = [
    "AAPL", "ADBE", "AMD", "CMCSA", "COST",
    "INTC", "INTU", "MSFT", "QCOM", "SBUX"
]

# --------------------------------------------------------------------------
# KHOẢNG THỜI GIAN DỮ LIỆU LỊCH SỬ CHO HUẤN LUYỆN OFFLINE (Batch Layer)
# - START_DATE: Ngày bắt đầu thu thập dữ liệu lịch sử
# - END_DATE: Ngày kết thúc dữ liệu huấn luyện offline
#   Dữ liệu từ END_DATE trở đi → dành cho streaming inference real-time
# --------------------------------------------------------------------------
START_DATE = "2005-01-01"
END_DATE = "2025-06-01"

# --------------------------------------------------------------------------
# CÁC CỘT ĐẶC TRƯNG (FEATURES) ĐẦU VÀO CHO MÔ HÌNH
# - Close: Giá đóng cửa
# - Volume: Khối lượng giao dịch
# - Return: Tỷ suất sinh lời hàng ngày = (Close_t - Close_{t-1}) / Close_{t-1}
# - MA5, MA20: Trung bình trượt 5 và 20 ngày
# - Volatility5, Volatility20: Độ biến động (std của Return) 5 và 20 ngày
# --------------------------------------------------------------------------
FEATURE_COLS = [
    "Close",
    "Volume",
    "Return",
    "MA5",
    "MA20",
    "Volatility5",
    "Volatility20"
]

TARGET_COL = "Close"
TARGET_IDX = FEATURE_COLS.index(TARGET_COL)

# --------------------------------------------------------------------------
# THAM SỐ CỬA SỔ THỜI GIAN
# - LOOKBACK: Số ngày lịch sử đưa vào LSTM (cửa sổ trượt)
# - DIRECTION_EPS: Ngưỡng epsilon để xác định hướng tăng/giảm
# --------------------------------------------------------------------------
LOOKBACK = 20
DIRECTION_EPS = 0.0

# --------------------------------------------------------------------------
# KÍCH THƯỚC MÔ HÌNH (MODEL DIMENSIONS)
# - LSTM_HIDDEN: Số neuron ẩn của LSTM (Temporal Block)
# - GNN_HIDDEN: Số neuron ẩn của GCN (Spatial Block)
# - MLP_HIDDEN: Số neuron ẩn của Prediction Head
# - DROPOUT: Tỷ lệ dropout chống overfitting
# --------------------------------------------------------------------------
LSTM_HIDDEN = 64
GNN_HIDDEN = 32
MLP_HIDDEN = 64
DROPOUT = 0.2

# --------------------------------------------------------------------------
# CẤU HÌNH EXPANDING WINDOW BACKTEST
# - EXP_WARM_START: Khởi tạo trọng số từ step trước (transfer learning)
# - EXP_TEST_DAYS: Số ngày cuối dùng để test (mỗi step test 1 ngày)
# - EXP_INITIAL_TRAIN_DAYS: Kích thước tập train ban đầu (2 năm giao dịch)
# - EXP_VAL_DAYS: Số ngày validation (tách từ cuối tập train)
# --------------------------------------------------------------------------
EXP_WARM_START = True
EXP_TEST_DAYS = 50
EXP_INITIAL_TRAIN_DAYS = 252 * 2
EXP_VAL_DAYS = 50

EXP_BATCH_SIZE = 11

EXP_USE_FAST_MODE = True

EXP_FAST_INIT_EPOCHS = 20
EXP_FAST_UPDATE_EPOCHS = 6
EXP_FAST_PATIENCE = 5

EXP_FINAL_INIT_EPOCHS = 40
EXP_FINAL_UPDATE_EPOCHS = 8
EXP_FINAL_PATIENCE = 5

EXP_INIT_EPOCHS = EXP_FAST_INIT_EPOCHS if EXP_USE_FAST_MODE else EXP_FINAL_INIT_EPOCHS
EXP_UPDATE_EPOCHS = EXP_FAST_UPDATE_EPOCHS if EXP_USE_FAST_MODE else EXP_FINAL_UPDATE_EPOCHS
EXP_PATIENCE = EXP_FAST_PATIENCE if EXP_USE_FAST_MODE else EXP_FINAL_PATIENCE

EXP_LR_LSTM = 0.005
EXP_LR_HYBRID = 0.005

# --------------------------------------------------------------------------
# CẤU HÌNH ĐỒ THỊ PEARSON CORRELATION
# - EXP_GRAPH_RECENT_DAYS: Số ngày gần nhất để tính tương quan
# - EXP_PEARSON_THRESHOLD: Ngưỡng |corr| tối thiểu để tạo cạnh
# - EXP_PEARSON_TOPK: Số lượng láng giềng tối đa mỗi node
# --------------------------------------------------------------------------
EXP_GRAPH_RECENT_DAYS = 252 * 2
EXP_PEARSON_THRESHOLD = 0.45
EXP_PEARSON_TOPK = 4

# --------------------------------------------------------------------------
# CẤU HÌNH ĐỒ THỊ ASSOCIATION RULE (Luật kết hợp đồng biến động)
# - EXP_ASSOC_MIN_SUPPORT: Ngưỡng support tối thiểu
# - EXP_ASSOC_MIN_CONFIDENCE: Ngưỡng confidence tối thiểu
# - EXP_ASSOC_LIFT_THRESHOLD: Ngưỡng lift tối thiểu để tạo cạnh
# - EXP_ASSOC_TOPK: Số láng giềng tối đa từ association graph
# - EXP_ASSOC_EDGE_WEIGHT: Trọng số khi kết hợp vào đồ thị chung
# --------------------------------------------------------------------------
EXP_ASSOC_RECENT_DAYS = 252 * 2
EXP_ASSOC_MIN_SUPPORT = 0.05
EXP_ASSOC_MIN_CONFIDENCE = 0.10
EXP_ASSOC_LIFT_THRESHOLD = 1.05
EXP_ASSOC_TOPK = 3
EXP_ASSOC_EDGE_WEIGHT = 0.50

# --------------------------------------------------------------------------
# ĐỒ THỊ KẾT HỢP CUỐI CÙNG
# - combined = max(pearson, weight * association), giữ top-K láng giềng
# --------------------------------------------------------------------------
EXP_FINAL_GRAPH_TOPK = 4

# --------------------------------------------------------------------------
# ROLLING MINMAXSCALER CHO INFERENCE REAL-TIME
# - ROLLING_SCALER_WINDOW: Số ngày cửa sổ trượt để fit scaler động
#   Đảm bảo giá hiện tại (2025-2026) luôn nằm trong [0,1]
#   thay vì dùng scaler tĩnh từ giai đoạn train (2005-2025)
# --------------------------------------------------------------------------
ROLLING_SCALER_WINDOW = 60

# --------------------------------------------------------------------------
# CẤU HÌNH RETRAIN ĐỊNH KỲ (Batch Layer - Airflow DAG)
# - RETRAIN_SCHEDULE: Cron expression cho lịch retrain
#   "0 0 1 */3 *" = ngày 1 mỗi quý, lúc 00:00
# - RETRAIN_MIN_NEW_DAYS: Số ngày dữ liệu mới tối thiểu để trigger retrain
# --------------------------------------------------------------------------
RETRAIN_SCHEDULE = "0 0 1 */3 *"
RETRAIN_MIN_NEW_DAYS = 20

SEED = 42