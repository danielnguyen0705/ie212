# src/evaluation.py
# ============================================================================
# MODULE ĐÁNH GIÁ TOÀN DIỆN: CHỈ SỐ MÔ HÌNH + CHỈ SỐ TÀI CHÍNH
# ============================================================================
#
# Module này cung cấp hai nhóm chỉ số đánh giá:
#
# NHÓM 1 — CHỈ SỐ MÔ HÌNH HỌC MÁY (Machine Learning Metrics):
#   Đo lường sai số giữa giá dự đoán và giá thực tế.
#   - MSE  (Mean Squared Error)
#   - RMSE (Root Mean Squared Error)
#   - MAE  (Mean Absolute Error)
#   - MAPE (Mean Absolute Percentage Error)
#   - R²   (Coefficient of Determination / R-squared)
#
# NHÓM 2 — CHỈ SỐ HIỆU QUẢ TÀI CHÍNH (Financial Trading Metrics):
#   Đo lường hiệu quả thực tế khi áp dụng dự đoán vào chiến lược giao dịch.
#   Bài toán Backtesting: Mua khi giá dự đoán tăng, Bán khi giá dự đoán giảm.
#   - Directional_Accuracy  (Độ chính xác hướng tăng/giảm)
#   - Cumulative_Return     (Lợi nhuận tích lũy chiến lược mô hình)
#   - BuyHold_Cumulative_Return (Lợi nhuận tích lũy chiến lược Mua-Giữ)
#   - Sharpe_Ratio          (Lợi nhuận điều chỉnh rủi ro - mô hình)
#   - BuyHold_Sharpe_Ratio  (Sharpe của chiến lược Mua-Giữ)
#   - Maximum_Drawdown      (Sụt giảm vốn lớn nhất - mô hình)
#   - BuyHold_Maximum_Drawdown (Sụt giảm vốn lớn nhất - Mua-Giữ)
#   - Win_Rate              (Tỷ lệ ngày có lời)
#   - Avg_Active_Positions  (Trung bình số mã đang giữ mỗi ngày)
#
# ============================================================================

from typing import Any, Dict, List, Optional

import numpy as np


# ============================================================================
# NHÓM 1: CHỈ SỐ MÔ HÌNH HỌC MÁY (MACHINE LEARNING METRICS)
# ============================================================================


def compute_mse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    MSE — Mean Squared Error (Sai số bình phương trung bình).

    Công thức toán học:
        MSE = (1/n) * Σ(y_i - ŷ_i)²

    Ý nghĩa:
        Đo lường trung bình bình phương sai lệch giữa giá thực và giá dự đoán.
        Giá trị MSE càng nhỏ → mô hình dự đoán càng chính xác.
        MSE phạt nặng các sai số lớn (do bình phương), nên nhạy cảm với outlier.

    Parameters
    ----------
    y_true : np.ndarray
        Giá đóng cửa thực tế, shape bất kỳ (sẽ được flatten)
    y_pred : np.ndarray
        Giá đóng cửa dự đoán, cùng shape với y_true

    Returns
    -------
    float
        Giá trị MSE >= 0
    """
    y_true_f = y_true.reshape(-1).astype(np.float64)
    y_pred_f = y_pred.reshape(-1).astype(np.float64)
    return float(np.mean((y_true_f - y_pred_f) ** 2))


def compute_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    RMSE — Root Mean Squared Error (Căn bậc hai sai số bình phương trung bình).

    Công thức toán học:
        RMSE = √MSE = √[(1/n) * Σ(y_i - ŷ_i)²]

    Ý nghĩa:
        Cùng đơn vị với biến mục tiêu (giá cổ phiếu), nên dễ diễn giải hơn MSE.
        Ví dụ: RMSE = 2.5 nghĩa là trung bình mô hình sai lệch khoảng $2.5.
        Vẫn nhạy cảm với outlier do kế thừa tính chất bình phương từ MSE.

    Returns
    -------
    float
        Giá trị RMSE >= 0
    """
    return float(np.sqrt(compute_mse(y_true, y_pred)))


def compute_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    MAE — Mean Absolute Error (Sai số tuyệt đối trung bình).

    Công thức toán học:
        MAE = (1/n) * Σ|y_i - ŷ_i|

    Ý nghĩa:
        Đo lường trung bình giá trị tuyệt đối sai lệch.
        Không phạt nặng outlier như MSE/RMSE.
        Cùng đơn vị với biến mục tiêu → trực quan.
        MAE = 1.8 nghĩa là trung bình mô hình sai khoảng $1.8 mỗi dự đoán.

    Returns
    -------
    float
        Giá trị MAE >= 0
    """
    y_true_f = y_true.reshape(-1).astype(np.float64)
    y_pred_f = y_pred.reshape(-1).astype(np.float64)
    return float(np.mean(np.abs(y_true_f - y_pred_f)))


def compute_mape(y_true: np.ndarray, y_pred: np.ndarray, eps: float = 1e-8) -> float:
    """
    MAPE — Mean Absolute Percentage Error (Sai số phần trăm tuyệt đối trung bình).

    Công thức toán học:
        MAPE = (1/n) * Σ(|y_i - ŷ_i| / |y_i|) * 100%

    Ý nghĩa:
        Thể hiện sai số dưới dạng phần trăm so với giá trị thực.
        Không phụ thuộc đơn vị → dễ so sánh giữa các mã cổ phiếu có mức giá khác nhau.
        MAPE = 1.25% nghĩa là trung bình sai lệch 1.25% so với giá thực.
        Lưu ý: MAPE không phù hợp khi y_true chứa giá trị gần 0.

    Parameters
    ----------
    eps : float
        Giá trị nhỏ tránh chia cho 0

    Returns
    -------
    float
        Giá trị MAPE tính theo tỷ lệ (0.0125 = 1.25%)
    """
    y_true_f = y_true.reshape(-1).astype(np.float64)
    y_pred_f = y_pred.reshape(-1).astype(np.float64)
    pct_errors = np.abs(y_true_f - y_pred_f) / (np.abs(y_true_f) + eps)
    return float(np.mean(pct_errors))


def compute_r_squared(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    R² — Coefficient of Determination (Hệ số xác định).

    Công thức toán học:
        R² = 1 - SS_res / SS_tot
        SS_res = Σ(y_i - ŷ_i)²     (Tổng bình phương phần dư)
        SS_tot = Σ(y_i - ȳ)²       (Tổng bình phương tổng thể)

    Ý nghĩa:
        Thể hiện tỷ lệ biến thiên của biến mục tiêu được giải thích bởi mô hình.
        - R² = 1.0: Mô hình dự đoán hoàn hảo
        - R² = 0.0: Mô hình không tốt hơn dự đoán bằng giá trị trung bình
        - R² < 0  : Mô hình tệ hơn cả dự đoán bằng trung bình
        R² = 0.885 nghĩa là mô hình giải thích 88.5% biến thiên giá cổ phiếu.

    Returns
    -------
    float
        Giá trị R², thường nằm trong [0, 1] cho mô hình tốt
    """
    y_true_f = y_true.reshape(-1).astype(np.float64)
    y_pred_f = y_pred.reshape(-1).astype(np.float64)

    ss_res = np.sum((y_true_f - y_pred_f) ** 2)
    ss_tot = np.sum((y_true_f - np.mean(y_true_f)) ** 2)

    if ss_tot < 1e-12:
        return 0.0

    return float(1.0 - ss_res / ss_tot)


def compute_ml_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Tính toán đầy đủ 5 chỉ số đánh giá mô hình học máy.

    Parameters
    ----------
    y_true : np.ndarray
        Giá đóng cửa thực tế
    y_pred : np.ndarray
        Giá đóng cửa dự đoán

    Returns
    -------
    dict
        Dictionary chứa: MSE, RMSE, MAE, MAPE, R_Squared
    """
    return {
        "MSE": compute_mse(y_true, y_pred),
        "RMSE": compute_rmse(y_true, y_pred),
        "MAE": compute_mae(y_true, y_pred),
        "MAPE": compute_mape(y_true, y_pred),
        "R_Squared": compute_r_squared(y_true, y_pred),
    }


# ============================================================================
# NHÓM 2: CHỈ SỐ HIỆU QUẢ TÀI CHÍNH (FINANCIAL TRADING METRICS)
# ============================================================================


def compute_directional_accuracy(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    last_close: np.ndarray,
    eps: float = 0.0,
) -> float:
    """
    Directional Accuracy — Độ chính xác hướng biến động tăng/giảm.

    Công thức toán học:
        DA = (1/n) * Σ 𝟙[sign(y_i - last_i) == sign(ŷ_i - last_i)]

        Trong đó 𝟙[·] là hàm chỉ thị (indicator function):
        = 1 nếu mô hình dự đoán đúng hướng (cùng tăng hoặc cùng giảm)
        = 0 nếu dự đoán sai hướng

    Ý nghĩa:
        Trong giao dịch thực tế, biết đúng hướng (tăng/giảm) quan trọng hơn
        biết chính xác giá. Nếu DA > 50%, mô hình dự đoán hướng tốt hơn
        đoán ngẫu nhiên (tung đồng xu).
        DA = 58.2% nghĩa là mô hình đoán đúng hướng 58.2% số ngày.

    Parameters
    ----------
    y_true : np.ndarray
        Giá đóng cửa thực tế ngày t, shape [num_samples, num_stocks]
    y_pred : np.ndarray
        Giá đóng cửa dự đoán ngày t
    last_close : np.ndarray
        Giá đóng cửa ngày t-1 (để xác định hướng biến động)
    eps : float
        Ngưỡng tối thiểu để xác định tăng/giảm (tránh nhiễu gần 0)

    Returns
    -------
    float
        Tỷ lệ dự đoán đúng hướng, trong khoảng [0, 1]
    """
    y_true_f = y_true.reshape(-1)
    y_pred_f = y_pred.reshape(-1)
    last_f = last_close.reshape(-1)

    true_up = (y_true_f - last_f) > eps
    pred_up = (y_pred_f - last_f) > eps

    return float(np.mean(true_up == pred_up))


def backtest_topk_long_short_strategy(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    last_close: np.ndarray,
    K: int = 2,
) -> Dict[str, Any]:
    """
    Backtesting chiến lược Top-K Long-Short Dollar-Neutral.
    Mua Top K mã dự đoán tăng mạnh nhất, Bán khống (Short) Bottom K mã dự báo giảm sâu nhất.
    """
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    last_close = np.asarray(last_close, dtype=np.float64)

    actual_returns = (y_true - last_close) / np.maximum(last_close, 1e-8)
    predicted_returns = (y_pred - last_close) / np.maximum(last_close, 1e-8)

    strategy_daily_returns = []

    for day_idx in range(y_true.shape[0]):
        pred_ret_day = predicted_returns[day_idx]
        actual_ret_day = actual_returns[day_idx]

        sorted_indices = np.argsort(pred_ret_day)

        short_indices = sorted_indices[:K]
        long_indices = sorted_indices[-K:]

        long_return = actual_ret_day[long_indices].mean()
        short_return = actual_ret_day[short_indices].mean()

        day_portfolio_return = long_return - short_return
        strategy_daily_returns.append(day_portfolio_return)

    strategy_daily_returns = np.asarray(strategy_daily_returns, dtype=np.float64)
    buyhold_daily_returns = actual_returns.mean(axis=1)

    strategy_portfolio = np.cumprod(1.0 + strategy_daily_returns)
    buyhold_portfolio = np.cumprod(1.0 + buyhold_daily_returns)

    return {
        "strategy_daily_returns": strategy_daily_returns,
        "buyhold_daily_returns": buyhold_daily_returns,
        "strategy_portfolio": strategy_portfolio,
        "buyhold_portfolio": buyhold_portfolio
    }


def backtest_long_only_strategy(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    last_close: np.ndarray,
    tickers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Backtesting chiến lược giao dịch dựa trên dự đoán mô hình.

    CHIẾN LƯỢC:
        - Mỗi ngày t, với mỗi cổ phiếu:
          + Nếu ŷ_t > last_close_{t-1} (dự đoán giá sẽ TĂNG) → MUA (giữ vị thế long)
          + Nếu ŷ_t <= last_close_{t-1} (dự đoán giá sẽ GIẢM) → KHÔNG GIỮ (flat)
        - Lợi nhuận mỗi ngày = Σ (r_actual_t * signal_t) / N_stocks
          với r_actual_t = (y_true_t - last_close_t) / last_close_t
          signal_t = 1 nếu dự đoán tăng, 0 nếu dự đoán giảm

    GIẢ ĐỊNH:
        - Phân bổ vốn đều cho tất cả cổ phiếu được chọn mua
        - Không tính phí giao dịch, không sử dụng đòn bẩy
        - Giao dịch tại giá đóng cửa

    Parameters
    ----------
    y_true : np.ndarray
        Giá thực tế, shape [num_days, num_stocks]
    y_pred : np.ndarray
        Giá dự đoán, shape [num_days, num_stocks]
    last_close : np.ndarray
        Giá ngày trước, shape [num_days, num_stocks]
    tickers : list of str, optional
        Danh sách tên cổ phiếu

    Returns
    -------
    dict
        Chứa: strategy_daily_returns, buyhold_daily_returns,
               strategy_portfolio, buyhold_portfolio,
               daily_positions, daily_num_active
    """
    num_days, num_stocks = y_true.shape

    # Tính tỷ suất sinh lời thực tế hàng ngày cho mỗi cổ phiếu
    # r_{i,t} = (y_true_{i,t} - last_close_{i,t}) / last_close_{i,t}
    actual_returns = (y_true - last_close) / (np.abs(last_close) + 1e-12)

    # Tín hiệu giao dịch: 1 = Mua (dự đoán tăng), 0 = Không giữ (dự đoán giảm)
    signals = (y_pred > last_close).astype(np.float32)  # [num_days, num_stocks]

    # Lợi nhuận chiến lược mô hình mỗi ngày:
    # Trung bình lợi nhuận có trọng số tín hiệu / tổng số cổ phiếu
    strategy_daily_returns = np.zeros(num_days, dtype=np.float64)
    daily_num_active = np.zeros(num_days, dtype=np.float64)

    for t in range(num_days):
        n_active = signals[t].sum()
        daily_num_active[t] = n_active

        if n_active > 0:
            # Phân bổ đều vốn cho các cổ phiếu được chọn mua
            strategy_daily_returns[t] = (actual_returns[t] * signals[t]).sum() / n_active
        else:
            # Không mua gì → lợi nhuận = 0 (giữ tiền mặt)
            strategy_daily_returns[t] = 0.0

    # Chiến lược Mua-Giữ (Buy & Hold): mua đều tất cả cổ phiếu từ đầu
    buyhold_daily_returns = actual_returns.mean(axis=1)  # [num_days]

    # Giá trị danh mục tích lũy (bắt đầu từ 1.0)
    strategy_portfolio = np.cumprod(1.0 + strategy_daily_returns)
    buyhold_portfolio = np.cumprod(1.0 + buyhold_daily_returns)

    return {
        "strategy_daily_returns": strategy_daily_returns,
        "buyhold_daily_returns": buyhold_daily_returns,
        "strategy_portfolio": strategy_portfolio,
        "buyhold_portfolio": buyhold_portfolio,
        "signals": signals,
        "daily_num_active": daily_num_active,
    }


def compute_cumulative_return(portfolio_values: np.ndarray) -> float:
    """
    Cumulative Return — Tổng lợi nhuận tích lũy.

    Công thức toán học:
        CR = (V_final / V_initial) - 1
        CR = V_final - 1  (khi V_initial = 1.0)

    Ý nghĩa:
        Tổng lợi nhuận từ đầu đến cuối kỳ backtesting.
        CR = 0.428 nghĩa là danh mục tăng 42.8% trong kỳ kiểm tra.
        So sánh CR của chiến lược mô hình với CR của Buy & Hold
        để đánh giá mô hình có tạo ra alpha (lợi nhuận vượt trội) không.

    Parameters
    ----------
    portfolio_values : np.ndarray
        Chuỗi giá trị danh mục tích lũy (bắt đầu từ 1.0)

    Returns
    -------
    float
        Lợi nhuận tích lũy dưới dạng tỷ lệ (0.428 = 42.8%)
    """
    if len(portfolio_values) == 0:
        return 0.0
    return float(portfolio_values[-1] - 1.0)


def compute_sharpe_ratio(
    daily_returns: np.ndarray,
    risk_free_rate: float = 0.0,
    trading_days: int = 252,
) -> float:
    """
    Sharpe Ratio — Lợi nhuận điều chỉnh theo rủi ro.

    Công thức toán học:
        Sharpe = [(r̄ - r_f) / σ_r] × √252

        Trong đó:
        - r̄  : lợi nhuận trung bình hàng ngày
        - r_f : lãi suất phi rủi ro hàng ngày (thường = 0 hoặc US T-bill / 252)
        - σ_r : độ lệch chuẩn lợi nhuận hàng ngày
        - √252: hệ số annualize (252 ngày giao dịch/năm)

    Ý nghĩa:
        Đo lường lượng lợi nhuận vượt trội trên mỗi đơn vị rủi ro.
        - Sharpe > 1.0  : Chiến lược tốt
        - Sharpe > 2.0  : Chiến lược rất tốt
        - Sharpe < 0    : Chiến lược thua lỗ hoặc thua lãi suất phi rủi ro
        Sharpe = 1.62 nghĩa là mỗi đơn vị rủi ro tạo ra 1.62 đơn vị lợi nhuận.

    Parameters
    ----------
    daily_returns : np.ndarray
        Chuỗi lợi nhuận hàng ngày
    risk_free_rate : float
        Lãi suất phi rủi ro hàng năm (mặc định 0)
    trading_days : int
        Số ngày giao dịch trong năm (mặc định 252)

    Returns
    -------
    float
        Giá trị Sharpe Ratio đã annualize
    """
    if len(daily_returns) < 2:
        return 0.0

    daily_rf = risk_free_rate / trading_days
    excess_returns = daily_returns - daily_rf
    std = np.std(excess_returns, ddof=1)

    if std < 1e-12:
        return 0.0

    return float((np.mean(excess_returns) / std) * np.sqrt(trading_days))


def compute_maximum_drawdown(portfolio_values: np.ndarray) -> float:
    """
    Maximum Drawdown (MDD) — Mức sụt giảm vốn lớn nhất.

    Công thức toán học:
        MDD = min_t [(V_t - V_peak_t) / V_peak_t]

        Trong đó:
        - V_t      : giá trị danh mục tại thời điểm t
        - V_peak_t : giá trị đỉnh cao nhất từ đầu đến thời điểm t
                     V_peak_t = max(V_1, V_2, ..., V_t)

    Ý nghĩa:
        Đo lường mức lỗ lớn nhất từ đỉnh đến đáy trong toàn bộ kỳ backtesting.
        MDD = -0.118 nghĩa là tại thời điểm tồi tệ nhất, danh mục giảm 11.8%
        so với đỉnh trước đó.
        MDD càng gần 0 → chiến lược càng ít rủi ro sụt giảm vốn.
        MDD luôn <= 0 (hoặc = 0 nếu danh mục chỉ tăng).

    Parameters
    ----------
    portfolio_values : np.ndarray
        Chuỗi giá trị danh mục tích lũy

    Returns
    -------
    float
        Giá trị MDD, luôn <= 0 (ví dụ: -0.118 = sụt giảm 11.8%)
    """
    if len(portfolio_values) < 2:
        return 0.0

    cumulative_max = np.maximum.accumulate(portfolio_values)
    drawdowns = (portfolio_values - cumulative_max) / (cumulative_max + 1e-12)

    return float(np.min(drawdowns))


def compute_win_rate(daily_returns: np.ndarray) -> float:
    """
    Win Rate — Tỷ lệ ngày chiến lược có lời.

    Công thức toán học:
        WR = (Số ngày r_t > 0) / (Tổng số ngày giao dịch)

    Ý nghĩa:
        Tỷ lệ ngày chiến lược sinh lời dương.
        WR = 0.545 nghĩa là 54.5% số ngày chiến lược có lời.
        WR > 50% là tín hiệu tích cực, nhưng cần kết hợp với Sharpe và MDD
        vì WR cao nhưng các ngày lỗ lỗ nặng thì chiến lược vẫn thua.

    Returns
    -------
    float
        Tỷ lệ trong khoảng [0, 1]
    """
    if len(daily_returns) == 0:
        return 0.0

    # Chỉ tính trên các ngày thực sự giao dịch (return != 0)
    active_days = daily_returns[daily_returns != 0.0]
    if len(active_days) == 0:
        return 0.0

    return float(np.mean(active_days > 0))


def compute_avg_active_positions(daily_num_active: np.ndarray) -> float:
    """
    Avg Active Positions — Số lượng cổ phiếu nắm giữ trung bình mỗi ngày.

    Công thức toán học:
        AAP = (1/D) * Σ_{t=1}^{D} N_active_t

        Trong đó N_active_t là số cổ phiếu được mua (signal=1) tại ngày t

    Ý nghĩa:
        Chỉ số diagnostic cho biết mức độ phân tán (diversification) của chiến lược.
        AAP = 3.6 trên 10 mã nghĩa là trung bình mỗi ngày chiến lược giữ 3.6 mã.
        AAP thấp → chiến lược tập trung (concentrated)
        AAP cao  → chiến lược phân tán (diversified)

    Returns
    -------
    float
        Số lượng trung bình >= 0
    """
    if len(daily_num_active) == 0:
        return 0.0
    return float(np.mean(daily_num_active))


# ============================================================================
# HÀM TỔNG HỢP: TÍNH TOÀN BỘ CHỈ SỐ
# ============================================================================


def compute_full_evaluation(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    last_close: np.ndarray,
    tickers: Optional[List[str]] = None,
    risk_free_rate: float = 0.0,
    direction_eps: float = 0.0,
) -> Dict[str, float]:
    """
    Tính toán toàn bộ chỉ số đánh giá (ML + Financial).

    Kết hợp cả hai nhóm chỉ số vào một dictionary duy nhất.

    Parameters
    ----------
    y_true : np.ndarray
        Giá thực tế, shape [num_days, num_stocks]
    y_pred : np.ndarray
        Giá dự đoán, shape [num_days, num_stocks]
    last_close : np.ndarray
        Giá ngày trước, shape [num_days, num_stocks]
    tickers : list of str, optional
        Danh sách tên cổ phiếu
    risk_free_rate : float
        Lãi suất phi rủi ro hàng năm
    direction_eps : float
        Ngưỡng epsilon cho directional accuracy

    Returns
    -------
    dict
        Dictionary chứa tất cả chỉ số đánh giá
    """
    # ---- NHÓM 1: Chỉ số mô hình học máy ----
    ml_metrics = compute_ml_metrics(y_true, y_pred)

    # ---- Directional Accuracy ----
    da = compute_directional_accuracy(y_true, y_pred, last_close, eps=direction_eps)

    # ---- NHÓM 2: Backtesting chiến lược tài chính ----
    bt = backtest_long_only_strategy(y_true, y_pred, last_close, tickers)

    strategy_cr = compute_cumulative_return(bt["strategy_portfolio"])
    buyhold_cr = compute_cumulative_return(bt["buyhold_portfolio"])

    strategy_sharpe = compute_sharpe_ratio(bt["strategy_daily_returns"], risk_free_rate)
    buyhold_sharpe = compute_sharpe_ratio(bt["buyhold_daily_returns"], risk_free_rate)

    strategy_mdd = compute_maximum_drawdown(bt["strategy_portfolio"])
    buyhold_mdd = compute_maximum_drawdown(bt["buyhold_portfolio"])

    win_rate = compute_win_rate(bt["strategy_daily_returns"])
    avg_positions = compute_avg_active_positions(bt["daily_num_active"])

    # ---- Tổng hợp kết quả ----
    result = {
        # Nhóm ML Metrics
        "MSE": ml_metrics["MSE"],
        "RMSE": ml_metrics["RMSE"],
        "MAE": ml_metrics["MAE"],
        "MAPE": ml_metrics["MAPE"],
        "R_Squared": ml_metrics["R_Squared"],
        # Nhóm Financial Metrics
        "Directional_Accuracy": da,
        "Cumulative_Return": strategy_cr,
        "BuyHold_Cumulative_Return": buyhold_cr,
        "Sharpe_Ratio": strategy_sharpe,
        "BuyHold_Sharpe_Ratio": buyhold_sharpe,
        "Maximum_Drawdown": strategy_mdd,
        "BuyHold_Maximum_Drawdown": buyhold_mdd,
        "Win_Rate": win_rate,
        "Avg_Active_Positions": avg_positions,
    }

    return result


def format_evaluation_report(metrics: Dict[str, float]) -> str:
    """
    Định dạng kết quả đánh giá thành bảng báo cáo dạng text.

    Parameters
    ----------
    metrics : dict
        Dictionary chứa tất cả chỉ số

    Returns
    -------
    str
        Bảng báo cáo dạng text có định dạng
    """
    lines = []
    lines.append("=" * 70)
    lines.append("BÁO CÁO ĐÁNH GIÁ TOÀN DIỆN MÔ HÌNH DỰ ĐOÁN GIÁ CỔ PHIẾU")
    lines.append("=" * 70)

    lines.append("\n--- NHÓM 1: CHỈ SỐ MÔ HÌNH HỌC MÁY ---")
    lines.append(f"  MSE  (Sai số bình phương trung bình)     : {metrics.get('MSE', 0):.6f}")
    lines.append(f"  RMSE (Căn bậc hai MSE)                   : {metrics.get('RMSE', 0):.6f}")
    lines.append(f"  MAE  (Sai số tuyệt đối trung bình)       : {metrics.get('MAE', 0):.6f}")
    lines.append(f"  MAPE (Sai số phần trăm trung bình)        : {metrics.get('MAPE', 0):.4%}")
    lines.append(f"  R²   (Hệ số xác định)                    : {metrics.get('R_Squared', 0):.4f}")

    lines.append("\n--- NHÓM 2: CHỈ SỐ HIỆU QUẢ TÀI CHÍNH ---")
    lines.append(f"  Directional Accuracy (Đúng hướng)         : {metrics.get('Directional_Accuracy', 0):.2%}")
    lines.append(f"  Cumulative Return (Chiến lược mô hình)    : {metrics.get('Cumulative_Return', 0):.2%}")
    lines.append(f"  BuyHold Cumulative Return (Mua-Giữ)       : {metrics.get('BuyHold_Cumulative_Return', 0):.2%}")
    lines.append(f"  Sharpe Ratio (Mô hình)                    : {metrics.get('Sharpe_Ratio', 0):.4f}")
    lines.append(f"  BuyHold Sharpe Ratio (Mua-Giữ)            : {metrics.get('BuyHold_Sharpe_Ratio', 0):.4f}")
    lines.append(f"  Maximum Drawdown (Mô hình)                : {metrics.get('Maximum_Drawdown', 0):.2%}")
    lines.append(f"  BuyHold Maximum Drawdown (Mua-Giữ)        : {metrics.get('BuyHold_Maximum_Drawdown', 0):.2%}")
    lines.append(f"  Win Rate (Tỷ lệ ngày có lời)              : {metrics.get('Win_Rate', 0):.2%}")
    lines.append(f"  Avg Active Positions (TB mã nắm giữ/ngày) : {metrics.get('Avg_Active_Positions', 0):.1f}")

    lines.append("\n" + "=" * 70)
    return "\n".join(lines)
