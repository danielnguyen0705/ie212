# src/rolling_scaler.py
# ============================================================================
# MODULE: ROLLING MINMAXSCALER CHO INFERENCE THỜI GIAN THỰC
# ============================================================================
#
# MỤC ĐÍCH:
#   Khi suy luận (inference) real-time, giá cổ phiếu hiện tại (năm 2025-2026)
#   có thể vượt xa vùng min-max của giai đoạn huấn luyện (2005-2025).
#   Nếu dùng MinMaxScaler tĩnh (fit trên train period), giá trị scaled sẽ
#   nằm ngoài [0, 1], làm sai lệch kết quả dự đoán.
#
# GIẢI PHÁP:
#   Sử dụng "Rolling MinMaxScaler" — chuẩn hóa động dựa trên cửa sổ
#   N ngày gần nhất (mặc định N=60). Với cửa sổ ngắn, biên độ giá trong
#   window tương đồng nhau → min-max scale tạo distribution gần với
#   distribution mà mô hình đã học trong quá trình training.
#
# CÔNG THỨC TOÁN HỌC:
#   Cho mỗi cổ phiếu j, mỗi đặc trưng f, cửa sổ W ngày gần nhất:
#
#     min_{j,f} = min(X[t-W+1:t+1, j, f])
#     max_{j,f} = max(X[t-W+1:t+1, j, f])
#
#     X_scaled[t, j, f] = (X[t, j, f] - min_{j,f}) / (max_{j,f} - min_{j,f} + eps)
#
#   Inverse transform cho giá đóng cửa dự đoán:
#     pred_real = pred_scaled * (close_max_j - close_min_j) + close_min_j
#
# ============================================================================

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np


class RollingMinMaxScaler:
    """
    Bộ chuẩn hóa Min-Max động (Rolling MinMaxScaler).

    Thay vì fit trên toàn bộ tập huấn luyện (tĩnh), bộ chuẩn hóa này
    fit trên cửa sổ trượt W ngày gần nhất. Điều này đảm bảo:
      1. Giá trị sau chuẩn hóa luôn nằm trong hoặc gần [0, 1]
      2. Distribution tương tự với dữ liệu training (vì biên độ giá
         trong cửa sổ ngắn ổn định hơn so với toàn bộ 20 năm)
      3. Mô hình inference real-time không bị ảnh hưởng bởi sự trôi dạt
         dữ liệu (data drift) theo thời gian

    Parameters
    ----------
    window_size : int
        Số ngày trong cửa sổ trượt để tính min/max (mặc định 60)
    eps : float
        Giá trị epsilon nhỏ tránh chia cho 0 khi max == min
    """

    def __init__(self, window_size: int = 60, eps: float = 1e-8):
        self.window_size = window_size
        self.eps = eps
        self.feature_mins: Optional[np.ndarray] = None
        self.feature_maxs: Optional[np.ndarray] = None
        self.close_mins: Optional[np.ndarray] = None
        self.close_maxs: Optional[np.ndarray] = None
        self.n_stocks: Optional[int] = None
        self.n_features: Optional[int] = None

    def fit(self, features_3d: np.ndarray, close_idx: int = 0) -> "RollingMinMaxScaler":
        """
        Fit scaler trên cửa sổ W ngày cuối cùng của tensor đặc trưng.

        Parameters
        ----------
        features_3d : np.ndarray
            Tensor đặc trưng có shape [T, N, F]
            - T: số ngày (time steps)
            - N: số cổ phiếu (nodes)
            - F: số đặc trưng (features)
        close_idx : int
            Chỉ số của cột Close trong F features (mặc định 0)

        Returns
        -------
        self
            Trả về chính đối tượng scaler để hỗ trợ method chaining
        """
        T, N, F = features_3d.shape
        self.n_stocks = N
        self.n_features = F

        # Xác định vùng cửa sổ: lấy W ngày cuối cùng
        # Nếu T < window_size, dùng toàn bộ dữ liệu có sẵn
        window_start = max(0, T - self.window_size)
        window_data = features_3d[window_start:T]  # [W, N, F]

        # Tính min, max theo chiều thời gian (axis=0) cho mỗi (stock, feature)
        # Kết quả: [N, F]
        self.feature_mins = window_data.min(axis=0).astype(np.float32)
        self.feature_maxs = window_data.max(axis=0).astype(np.float32)

        # Lưu riêng min/max của cột Close để inverse transform sau này
        # Kết quả: [N]
        self.close_mins = self.feature_mins[:, close_idx].copy()
        self.close_maxs = self.feature_maxs[:, close_idx].copy()

        return self

    def transform(self, features_3d: np.ndarray) -> np.ndarray:
        """
        Chuẩn hóa dữ liệu bằng min/max đã fit.

        Công thức: X_scaled = (X - min) / (max - min + eps)

        Parameters
        ----------
        features_3d : np.ndarray
            Tensor [T, N, F] hoặc [N, F] cần chuẩn hóa

        Returns
        -------
        np.ndarray
            Tensor đã chuẩn hóa, cùng shape với input
        """
        if self.feature_mins is None or self.feature_maxs is None:
            raise RuntimeError("Scaler chưa được fit. Gọi fit() trước khi transform().")

        mins = self.feature_mins  # [N, F]
        ranges = self.feature_maxs - self.feature_mins + self.eps  # [N, F]

        # Broadcasting: features_3d [T, N, F] hoặc [N, F]
        # mins và ranges đều là [N, F] → tự broadcast theo chiều T
        scaled = (features_3d.astype(np.float32) - mins) / ranges
        return scaled.astype(np.float32)

    def fit_transform(self, features_3d: np.ndarray, close_idx: int = 0) -> np.ndarray:
        """
        Fit trên cửa sổ cuối cùng, sau đó transform toàn bộ dữ liệu.

        Parameters
        ----------
        features_3d : np.ndarray
            Tensor [T, N, F]
        close_idx : int
            Chỉ số cột Close

        Returns
        -------
        np.ndarray
            Tensor đã chuẩn hóa [T, N, F]
        """
        self.fit(features_3d, close_idx=close_idx)
        return self.transform(features_3d)

    def inverse_transform_close(self, pred_scaled: np.ndarray) -> np.ndarray:
        """
        Chuyển đổi ngược giá đóng cửa đã scaled về giá thực.

        Công thức: pred_real = pred_scaled * (close_max - close_min) + close_min

        Parameters
        ----------
        pred_scaled : np.ndarray
            Giá đóng cửa đã chuẩn hóa, shape [B, N] hoặc [N]

        Returns
        -------
        np.ndarray
            Giá đóng cửa thực, cùng shape với input
        """
        if self.close_mins is None or self.close_maxs is None:
            raise RuntimeError("Scaler chưa được fit. Không thể inverse transform.")

        close_range = self.close_maxs - self.close_mins  # [N]
        pred_real = pred_scaled * close_range + self.close_mins
        return pred_real.astype(np.float32)

    def get_scaler_params(self) -> Dict[str, np.ndarray]:
        """
        Trả về các tham số scaler dưới dạng dictionary numpy arrays.
        Dùng để serialize vào file .npz khi build inference bundle.

        Returns
        -------
        dict
            Dictionary chứa: feature_mins, feature_maxs, close_mins, close_maxs
        """
        if self.feature_mins is None:
            raise RuntimeError("Scaler chưa được fit.")

        return {
            "scaler_feature_mins": self.feature_mins,
            "scaler_feature_maxs": self.feature_maxs,
            "scaler_close_mins": self.close_mins,
            "scaler_close_maxs": self.close_maxs,
            "scaler_window_size": np.array(self.window_size, dtype=np.int32),
        }

    @classmethod
    def from_npz_params(cls, npz_data: dict) -> "RollingMinMaxScaler":
        """
        Khôi phục scaler từ các tham số đã lưu trong file .npz.

        Parameters
        ----------
        npz_data : dict
            Dictionary chứa các key scaler_* từ file .npz

        Returns
        -------
        RollingMinMaxScaler
            Đối tượng scaler đã được khôi phục
        """
        window_size = int(npz_data["scaler_window_size"])
        scaler = cls(window_size=window_size)
        scaler.feature_mins = npz_data["scaler_feature_mins"].astype(np.float32)
        scaler.feature_maxs = npz_data["scaler_feature_maxs"].astype(np.float32)
        scaler.close_mins = npz_data["scaler_close_mins"].astype(np.float32)
        scaler.close_maxs = npz_data["scaler_close_maxs"].astype(np.float32)
        scaler.n_stocks = scaler.feature_mins.shape[0]
        scaler.n_features = scaler.feature_mins.shape[1]
        return scaler

    def save_json(self, path: str) -> None:
        """
        Lưu tham số scaler ra file JSON (cho mục đích debug/giám sát).

        Parameters
        ----------
        path : str
            Đường dẫn file JSON output
        """
        if self.feature_mins is None:
            raise RuntimeError("Scaler chưa được fit.")

        data = {
            "window_size": self.window_size,
            "n_stocks": int(self.n_stocks),
            "n_features": int(self.n_features),
            "close_mins": self.close_mins.tolist(),
            "close_maxs": self.close_maxs.tolist(),
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load_json(cls, path: str) -> "RollingMinMaxScaler":
        """
        Load tham số scaler từ file JSON.

        Parameters
        ----------
        path : str
            Đường dẫn file JSON

        Returns
        -------
        RollingMinMaxScaler
            Scaler đã khôi phục (chỉ có close_mins/close_maxs)
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        scaler = cls(window_size=data["window_size"])
        scaler.n_stocks = data["n_stocks"]
        scaler.n_features = data["n_features"]
        scaler.close_mins = np.array(data["close_mins"], dtype=np.float32)
        scaler.close_maxs = np.array(data["close_maxs"], dtype=np.float32)
        return scaler
