# src/expanding.py
# ============================================================================
# MODULE EXPANDING WINDOW: Chia dữ liệu + Xây dựng mẫu huấn luyện
# ============================================================================
#
# EXPANDING WINDOW BACKTEST:
#   Phương pháp đánh giá mô hình chuỗi thời gian tài chính.
#   - Bắt đầu với tập train kích thước cố định (504 ngày = 2 năm)
#   - Mỗi bước, test 1 ngày tiếp theo
#   - Tập train MỞ RỘNG thêm 1 ngày (expanding, không phải sliding)
#   - Đồ thị cổ phiếu được TÁI XÂY DỰNG mỗi bước
#
#   Minh họa (50 bước):
#   Step 1: Train [0..4729]          Test [4730]
#   Step 2: Train [0..4730]          Test [4731]  ← train mở rộng +1
#   Step 3: Train [0..4731]          Test [4732]
#   ...
#   Step 50: Train [0..4778]         Test [4779]
#
# ============================================================================

import json
from pathlib import Path

import numpy as np
from sklearn.preprocessing import MinMaxScaler

from src.config import TARGET_IDX


def fit_and_scale_for_expanding_initial_window(raw_features_3d, first_test_t, initial_train_days):
    """
    Fit MinMaxScaler trên cửa sổ train ban đầu và scale toàn bộ dữ liệu.

    Quy trình:
        1. Xác định vùng train: [first_test_t - initial_train_days, first_test_t - 1]
        2. Fit MinMaxScaler riêng cho mỗi cổ phiếu (vì mỗi mã có thang giá khác nhau)
        3. Transform toàn bộ chuỗi thời gian (kể cả ngoài vùng train)

    Lưu ý: Scaler fit trên train data rồi transform toàn bộ → test data
    có thể có giá trị ngoài [0,1] nếu giá vượt range train. Đây là hạn chế
    của MinMaxScaler tĩnh, được giải quyết bằng RollingMinMaxScaler cho inference.

    Parameters
    ----------
    raw_features_3d : np.ndarray [T, N, F]
        Tensor đặc trưng thô (chưa scale)
    first_test_t : int
        Chỉ số thời gian bắt đầu test (ngày test đầu tiên)
    initial_train_days : int
        Số ngày train ban đầu (504 = 2 năm giao dịch)

    Returns
    -------
    scaled : np.ndarray [T, N, F]
        Tensor đã chuẩn hóa
    scalers : list of MinMaxScaler
        Danh sách scaler cho mỗi cổ phiếu (để inverse transform nếu cần)
    close_mins : np.ndarray [N]
        Giá Close tối thiểu mỗi mã (trong vùng train)
    close_maxs : np.ndarray [N]
        Giá Close tối đa mỗi mã (trong vùng train)
    train_start_t : int
        Chỉ số bắt đầu train
    train_end_t : int
        Chỉ số kết thúc train
    """
    T, N, F = raw_features_3d.shape

    train_start_t = max(0, first_test_t - initial_train_days)
    train_end_t = first_test_t - 1

    scaled = np.zeros_like(raw_features_3d, dtype=np.float32)
    scalers = []
    close_mins = []
    close_maxs = []

    for j in range(N):
        scaler = MinMaxScaler()
        # Fit chỉ trên vùng train
        scaler.fit(raw_features_3d[train_start_t:train_end_t + 1, j, :])

        # Transform toàn bộ chuỗi (bao gồm cả test)
        scaled[:, j, :] = scaler.transform(raw_features_3d[:, j, :]).astype(np.float32)
        scalers.append(scaler)

        # Lưu min/max của Close để inverse transform sau này
        close_mins.append(float(scaler.data_min_[TARGET_IDX]))
        close_maxs.append(float(scaler.data_max_[TARGET_IDX]))

    return scaled, scalers, np.array(close_mins), np.array(close_maxs), train_start_t, train_end_t


def build_samples_for_target_range(close_only_3d, full_node_3d, adj_norm,
                                   start_t, end_t, lookback, dates, target_idx):
    """
    Xây dựng các mẫu (samples) cho một khoảng thời gian chỉ định.

    Mỗi mẫu tại thời điểm t bao gồm:
        - X_seq:      Chuỗi Close 20 ngày [N, T, 1] (input LSTM)
        - X_node:     7 features tại ngày t-1 [N, 7] (input GCN)
        - A:          Ma trận kề [N, N] (input GCN)
        - y_res:      Biến động giá: y_close - last_close [N] (target residual)
        - y_close:    Giá đóng cửa thực tại ngày t [N] (target chính)
        - last_close: Giá đóng cửa ngày t-1 [N] (baseline để cộng residual)

    Mô hình dự đoán: ŷ = last_close + model(X_seq, X_node, A)

    Parameters
    ----------
    close_only_3d : np.ndarray [T, N, 1]
        Chuỗi giá Close đã scaled
    full_node_3d : np.ndarray [T, N, F]
        Tensor đầy đủ 7 features đã scaled
    adj_norm : np.ndarray [N, N]
        Ma trận kề đã chuẩn hóa
    start_t, end_t : int
        Khoảng thời gian xây dựng mẫu
    lookback : int
        Độ dài cửa sổ lịch sử (20)
    dates : DatetimeIndex
        Danh sách ngày
    target_idx : int
        Chỉ số cột Close trong tensor features

    Returns
    -------
    dict
        Dictionary chứa X_seq, X_node, A, y_res, y_close, last_close, dates
    """
    X_seq_list = []
    X_node_list = []
    A_list = []
    y_res_list = []
    y_close_list = []
    last_close_list = []
    date_list = []

    for t in range(start_t, end_t + 1):
        if t - lookback < 0:
            continue

        # Chuỗi Close 20 ngày trước đó: [lookback, N, 1]
        seq = close_only_3d[t - lookback:t, :, :]
        # Transpose thành [N, lookback, 1] cho LSTM (mỗi stock 1 chuỗi)
        seq = np.transpose(seq, (1, 0, 2))

        # Đặc trưng node tại ngày t-1 (ngày gần nhất đã biết)
        node_x = full_node_3d[t - 1, :, :]

        # Target: giá Close thực tại ngày t
        target_close = full_node_3d[t, :, target_idx]

        # Baseline: giá Close ngày t-1
        last_close = full_node_3d[t - 1, :, target_idx]

        # Residual: biến động giá cần dự đoán
        target_res = target_close - last_close

        X_seq_list.append(seq.astype(np.float32))
        X_node_list.append(node_x.astype(np.float32))
        A_list.append(adj_norm.astype(np.float32))
        y_res_list.append(target_res.astype(np.float32))
        y_close_list.append(target_close.astype(np.float32))
        last_close_list.append(last_close.astype(np.float32))
        date_list.append(dates[t])

    X_seq = np.stack(X_seq_list)
    X_node = np.stack(X_node_list)
    A = np.stack(A_list)
    y_res = np.stack(y_res_list)
    y_close = np.stack(y_close_list)
    last_close = np.stack(last_close_list)
    date_list = np.array(date_list)

    return {
        "X_seq": X_seq,
        "X_node": X_node,
        "A": A,
        "y_res": y_res,
        "y_close": y_close,
        "last_close": last_close,
        "dates": date_list
    }


from src.dataset import StockGraphDataset


def pack_to_dataset(pack):
    """Chuyển dictionary mẫu thành PyTorch Dataset."""
    return StockGraphDataset(
        X_seq=pack["X_seq"],
        X_node=pack["X_node"],
        A=pack["A"],
        y_res=pack["y_res"],
        y_close=pack["y_close"],
        last_close=pack["last_close"]
    )


from src.config import (
    EXP_TEST_DAYS,
    EXP_INITIAL_TRAIN_DAYS,
    TARGET_IDX,
)
from src.graph_builder import build_combined_graph_from_train_window


def prepare_expanding_step_data(
    test_t,
    lookback,
    val_days,
    dates,
    return_2d,
    close_only_3d,
    full_node_3d,
    tickers
):
    """
    Chuẩn bị dữ liệu cho một bước expanding window.

    Quy trình:
        1. Xác định vùng train: [train_start_t, test_t - 1]
        2. Xây dựng đồ thị cổ phiếu mới (dựa trên train data hiện tại)
        3. Tạo mẫu train + val + test
        4. Val = val_days ngày cuối tập train (để early stopping)
        5. Test = 1 ngày (test_t)

    Parameters
    ----------
    test_t : int
        Chỉ số ngày test
    lookback : int
        Cửa sổ lịch sử LSTM
    val_days : int
        Số ngày validation
    dates : DatetimeIndex
        Danh sách ngày
    return_2d : np.ndarray [T, N]
        Ma trận return
    close_only_3d : np.ndarray [T, N, 1]
        Giá Close đã scaled
    full_node_3d : np.ndarray [T, N, F]
        Features đầy đủ đã scaled
    tickers : list of str
        Danh sách mã

    Returns
    -------
    train_pack, val_pack, test_pack : dict
        Các dictionary mẫu cho train/val/test
    meta : dict
        Metadata: adj_norm, adj_raw, corr_raw, graph_debug, test_date
    """
    first_test_t = len(dates) - EXP_TEST_DAYS
    train_start_t = max(0, first_test_t - EXP_INITIAL_TRAIN_DAYS)
    train_end_t = test_t - 1

    # Xây dựng lại đồ thị cổ phiếu dựa trên dữ liệu train MỚI NHẤT
    # Điều này đảm bảo đồ thị phản ánh tương quan hiện tại, không phải quá khứ xa
    adj_norm, adj_raw, corr_raw, graph_debug = build_combined_graph_from_train_window(
        return_2d=return_2d,
        tickers=tickers,
        train_start_t=train_start_t,
        train_end_t=train_end_t
    )

    sample_start_t = max(train_start_t + lookback, lookback)

    # Xây dựng mẫu cho toàn bộ vùng train + val
    all_trainval = build_samples_for_target_range(
        close_only_3d=close_only_3d,
        full_node_3d=full_node_3d,
        adj_norm=adj_norm,
        start_t=sample_start_t,
        end_t=train_end_t,
        lookback=lookback,
        dates=dates,
        target_idx=TARGET_IDX
    )

    n_total = len(all_trainval["y_close"])
    if n_total <= val_days:
        raise ValueError("Không đủ train samples để tách validation.")

    # Tách val_days ngày cuối làm validation (cho early stopping)
    split_idx = n_total - val_days

    train_pack = {
        k: v[:split_idx] if isinstance(v, np.ndarray) else v
        for k, v in all_trainval.items()
    }
    val_pack = {
        k: v[split_idx:] if isinstance(v, np.ndarray) else v
        for k, v in all_trainval.items()
    }

    # Test: chỉ 1 ngày (test_t)
    test_pack = build_samples_for_target_range(
        close_only_3d=close_only_3d,
        full_node_3d=full_node_3d,
        adj_norm=adj_norm,
        start_t=test_t,
        end_t=test_t,
        lookback=lookback,
        dates=dates,
        target_idx=TARGET_IDX
    )

    meta = {
        "test_t": test_t,
        "test_date": dates[test_t],
        "train_start_t": train_start_t,
        "train_end_t": train_end_t,
        "adj_norm": adj_norm,
        "adj_raw": adj_raw,
        "corr_raw": corr_raw,
        "graph_debug": graph_debug
    }

    return train_pack, val_pack, test_pack, meta


# ============================================================================
# SAVE / LOAD SCALER PARAMS (cho inference pipeline)
# ============================================================================


def save_scalers(scalers, path: str):
    """
    Serialize danh sách MinMaxScaler thành JSON.

    Lưu data_min_ và data_max_ của mỗi scaler để có thể
    inverse transform kết quả dự đoán về giá thực.

    Parameters
    ----------
    scalers : list of MinMaxScaler
        Danh sách scaler, mỗi cổ phiếu 1 scaler
    path : str
        Đường dẫn file JSON output
    """
    data = []
    for s in scalers:
        data.append({
            "data_min": s.data_min_.tolist(),
            "data_max": s.data_max_.tolist(),
            "feature_range": list(s.feature_range),
        })

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_scalers(path: str):
    """
    Load danh sách MinMaxScaler từ file JSON.

    Parameters
    ----------
    path : str
        Đường dẫn file JSON

    Returns
    -------
    list of MinMaxScaler
        Danh sách scaler đã khôi phục
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    scalers = []
    for item in data:
        scaler = MinMaxScaler(feature_range=tuple(item["feature_range"]))
        scaler.data_min_ = np.array(item["data_min"], dtype=np.float64)
        scaler.data_max_ = np.array(item["data_max"], dtype=np.float64)
        scaler.data_range_ = scaler.data_max_ - scaler.data_min_
        scaler.scale_ = 1.0 / (scaler.data_range_ + 1e-12)
        scaler.min_ = -scaler.data_min_ * scaler.scale_
        scaler.n_features_in_ = len(scaler.data_min_)
        scaler.n_samples_seen_ = 1
        scalers.append(scaler)

    return scalers
