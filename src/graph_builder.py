# src/graph_builder.py
# ============================================================================
# MODULE XÂY DỰNG ĐỒ THỊ CỔ PHIẾU (Stock Graph Construction)
# ============================================================================
#
# Module này xây dựng ma trận kề (adjacency matrix) thể hiện mối quan hệ
# giữa các cổ phiếu dựa trên 2 phương pháp:
#
# 1. ĐỒ THỊ PEARSON CORRELATION:
#    Đo lường tương quan tuyến tính giữa chuỗi tỷ suất sinh lời (return)
#    của các cặp cổ phiếu. Nếu |corr(i,j)| > threshold → tạo cạnh.
#    Ý nghĩa: Hai cổ phiếu có giá biến động cùng chiều/ngược chiều mạnh.
#
# 2. ĐỒ THỊ ASSOCIATION RULE (Luật kết hợp):
#    Phân tích tần suất đồng biến động (cùng tăng/cùng giảm) giữa các cặp
#    cổ phiếu dựa trên 3 chỉ số: Support, Confidence, Lift.
#    Ý nghĩa: Khi cổ phiếu A tăng, cổ phiếu B có xu hướng tăng theo.
#
# 3. ĐỒ THỊ KẾT HỢP (Combined Graph):
#    combined = max(pearson_weight, α × association_weight)
#    Giữ top-K láng giềng, chuẩn hóa đối xứng D^{-1/2} A D^{-1/2}
#
# ĐỒ THỊ ĐƯỢC TÁI XÂY DỰNG MỖI EXPANDING WINDOW STEP:
#    Khi tập training mở rộng, tương quan giữa các cổ phiếu có thể thay đổi.
#    Hệ thống tự động tính lại đồ thị dựa trên EXP_GRAPH_RECENT_DAYS ngày
#    giao dịch gần nhất trong cửa sổ training.
#
# ============================================================================

import numpy as np

from src.config import (
    EXP_GRAPH_RECENT_DAYS,
    EXP_PEARSON_THRESHOLD,
    EXP_PEARSON_TOPK,
    EXP_ASSOC_RECENT_DAYS,
    EXP_ASSOC_MIN_SUPPORT,
    EXP_ASSOC_MIN_CONFIDENCE,
    EXP_ASSOC_LIFT_THRESHOLD,
    EXP_ASSOC_TOPK,
    EXP_ASSOC_EDGE_WEIGHT,
    EXP_FINAL_GRAPH_TOPK,
)


def normalize_adjacency(adj: np.ndarray) -> np.ndarray:
    """
    Chuẩn hóa đối xứng ma trận kề: Â = D^{-1/2} · A · D^{-1/2}

    Công thức toán học:
        D = diag(Σ_j A_{ij})          — Ma trận bậc (degree matrix)
        D^{-1/2} = diag(d_i^{-0.5})   — Nghịch đảo căn bậc hai bậc
        Â = D^{-1/2} · A · D^{-1/2}   — Ma trận kề chuẩn hóa

    Ý nghĩa:
        Chuẩn hóa đối xứng đảm bảo:
        1. Tổng trọng số cạnh của mỗi node được bình thường hóa
        2. Node có nhiều cạnh (bậc cao) sẽ có trọng số mỗi cạnh nhỏ hơn
        3. Tránh exploding/vanishing gradients khi message passing nhiều lớp
        Đây là phương pháp chuẩn hóa trong GCN gốc của Kipf & Welling (2017).

    Parameters
    ----------
    adj : np.ndarray [N, N]
        Ma trận kề thô (chưa chuẩn hóa)

    Returns
    -------
    np.ndarray [N, N]
        Ma trận kề đã chuẩn hóa đối xứng
    """
    adj = adj.astype(np.float32)

    # Tính bậc mỗi node: d_i = Σ_j A_{ij}
    deg = adj.sum(axis=1)

    # D^{-1/2}: tránh chia 0 bằng max(deg, 1e-8)
    deg_inv_sqrt = np.power(np.maximum(deg, 1e-8), -0.5)
    D_inv_sqrt = np.diag(deg_inv_sqrt)

    # Â = D^{-1/2} · A · D^{-1/2}
    adj_norm = D_inv_sqrt @ adj @ D_inv_sqrt

    return adj_norm.astype(np.float32)


def sparsify_keep_topk(weight_mat, topk, keep_self=True):
    """
    Giữ lại top-K cạnh có trọng số lớn nhất cho mỗi node.

    Mục đích:
        Đồ thị đầy đủ (fully connected) có N² cạnh → quá dày đặc.
        Giữ top-K cạnh mạnh nhất giúp:
        1. Giảm nhiễu: loại bỏ cạnh yếu (tương quan ngẫu nhiên)
        2. Tăng hiệu quả tính toán: ma trận kề thưa (sparse)
        3. Tăng khả năng diễn giải: chỉ giữ quan hệ quan trọng nhất

    Parameters
    ----------
    weight_mat : np.ndarray [N, N]
        Ma trận trọng số cạnh
    topk : int
        Số cạnh tối đa giữ lại cho mỗi node
    keep_self : bool
        Có giữ self-loop (A_{ii}=1) hay không

    Returns
    -------
    np.ndarray [N, N]
        Ma trận thưa, đối xứng, chỉ giữ top-K cạnh mỗi node
    """
    N = weight_mat.shape[0]
    out = np.zeros_like(weight_mat, dtype=np.float32)

    for i in range(N):
        row = weight_mat[i].copy()
        row[i] = 0.0  # Bỏ self-loop khỏi ranking

        # Lấy các cạnh có trọng số dương
        pos_idx = np.where(row > 0)[0]
        if len(pos_idx) > 0:
            # Sắp xếp giảm dần, lấy top-K
            chosen = pos_idx[np.argsort(row[pos_idx])[::-1][:topk]]
            out[i, chosen] = row[chosen]

    # Đối xứng hóa: nếu i→j tồn tại thì j→i cũng tồn tại
    out = np.maximum(out, out.T)

    # Thêm self-loop nếu cần (mỗi node kết nối với chính nó)
    if keep_self:
        np.fill_diagonal(out, 1.0)

    return out.astype(np.float32)


def build_sparse_pearson_graph_from_train_window(
    return_2d,
    train_start_t,
    train_end_t,
    recent_days=504,
    threshold=0.70,
    topk=5
):
    """
    Xây dựng đồ thị dựa trên hệ số tương quan Pearson.

    Quy trình:
        1. Lấy chuỗi Return của recent_days ngày gần nhất trong train window
        2. Tính ma trận tương quan Pearson giữa tất cả các cặp cổ phiếu
        3. Lọc: chỉ giữ cạnh có |corr| ≥ threshold
        4. Sparsify: giữ top-K láng giềng mỗi node

    Công thức Pearson:
        corr(i,j) = Cov(r_i, r_j) / (σ_i × σ_j)

        Trong đó r_i, r_j là chuỗi return của cổ phiếu i và j

    Ý nghĩa ngưỡng:
        threshold = 0.70: Chỉ kết nối các cổ phiếu có tương quan
        tuyến tính mạnh (|corr| ≥ 0.70). Ví dụ: AAPL và MSFT
        thường có tương quan cao vì cùng là Big Tech.

    Parameters
    ----------
    return_2d : np.ndarray [T, N]
        Ma trận tỷ suất sinh lời hàng ngày
    train_start_t, train_end_t : int
        Chỉ số thời gian bắt đầu/kết thúc tập training
    recent_days : int
        Số ngày gần nhất để tính tương quan (mặc định 504 = 2 năm)
    threshold : float
        Ngưỡng |corr| tối thiểu (mặc định 0.70)
    topk : int
        Số láng giềng tối đa (mặc định 5)

    Returns
    -------
    pearson_raw : np.ndarray [N, N]
        Ma trận kề Pearson (thưa, đối xứng)
    corr : np.ndarray [N, N]
        Ma trận tương quan đầy đủ (để phân tích)
    """
    # Xác định vùng tính tương quan: recent_days ngày cuối trong train window
    graph_start_t = max(train_start_t, train_end_t - recent_days + 1)
    train_returns = return_2d[graph_start_t:train_end_t + 1].copy()

    # Tính ma trận tương quan Pearson: [N, N]
    corr = np.corrcoef(train_returns.T)
    corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)

    # Lấy giá trị tuyệt đối (quan tâm cả tương quan dương lẫn âm)
    pearson_raw = np.abs(corr).astype(np.float32)

    # Lọc theo ngưỡng: cạnh yếu (|corr| < threshold) → trọng số = 0
    pearson_raw[pearson_raw < threshold] = 0.0
    np.fill_diagonal(pearson_raw, 1.0)  # Self-loop

    # Giữ top-K cạnh mạnh nhất mỗi node
    pearson_raw = sparsify_keep_topk(pearson_raw, topk=topk, keep_self=True)

    return pearson_raw, corr


def build_manual_association_graph_from_train_window(
    return_2d,
    tickers,
    train_start_t,
    train_end_t,
    recent_days=504,
    min_support=0.05,
    min_confidence=0.10,
    lift_threshold=1.70,
    topk=5
):
    """
    Xây dựng đồ thị dựa trên Luật kết hợp (Association Rules) đồng biến động.

    Quy trình:
        1. Xác định ngày tăng (return > 0) và ngày giảm (return < 0) cho mỗi mã
        2. Với mỗi cặp (i, j), tính:
           - Support: P(i∧j) = tần suất cùng tăng hoặc cùng giảm
           - Confidence: P(j|i) = xác suất j tăng khi i tăng
           - Lift: P(i∧j) / [P(i)×P(j)] = mức độ "bất ngờ" so với độc lập
        3. Lọc: chỉ giữ cạnh thỏa mãn ĐỒng thời 3 điều kiện:
           support ≥ min_support AND confidence ≥ min_confidence AND lift ≥ lift_threshold

    Công thức toán học:
        Support(i→j) = P(cùng tăng hoặc cùng giảm)
        Confidence(i→j) = P(j tăng | i tăng) hoặc P(j giảm | i giảm)
        Lift(i→j) = P(i∧j) / [P(i) × P(j)]

    Ý nghĩa Lift:
        - Lift = 1.0: i và j biến động độc lập
        - Lift > 1.0: i và j có xu hướng đồng biến động (mạnh hơn ngẫu nhiên)
        - Lift > 1.5: Quan hệ đồng biến động đáng kể

    Parameters
    ----------
    return_2d : np.ndarray [T, N]
        Ma trận tỷ suất sinh lời
    tickers : list of str
        Danh sách mã cổ phiếu
    train_start_t, train_end_t : int
        Phạm vi training
    recent_days : int
        Số ngày gần nhất (mặc định 504)
    min_support, min_confidence : float
        Ngưỡng support và confidence tối thiểu
    lift_threshold : float
        Ngưỡng lift tối thiểu (mặc định 1.70)
    topk : int
        Số láng giềng tối đa

    Returns
    -------
    assoc_raw : np.ndarray [N, N]
        Ma trận kề Association Rule (thưa, đối xứng, chuẩn hóa [0,1])
    debug_info : dict
        Thông tin debug (số cạnh, xác suất trung bình up/down)
    """
    graph_start_t = max(train_start_t, train_end_t - recent_days + 1)
    train_returns = return_2d[graph_start_t:train_end_t + 1].copy()

    # Xác định ngày tăng/giảm cho mỗi cổ phiếu
    up = (train_returns > 0).astype(np.float32)    # [T', N] — 1 nếu tăng, 0 nếu không
    down = (train_returns < 0).astype(np.float32)  # [T', N] — 1 nếu giảm

    _, N = up.shape
    assoc_raw = np.zeros((N, N), dtype=np.float32)

    # P(mã i tăng), P(mã i giảm)
    p_up = up.mean(axis=0)    # [N]
    p_down = down.mean(axis=0)  # [N]

    for i in range(N):
        for j in range(N):
            if i == j:
                continue

            # Tính cho trường hợp CÙNG TĂNG
            both_up = (up[:, i] * up[:, j]).mean()           # P(i∧j cùng tăng)
            conf_up = both_up / (p_up[i] + 1e-8)             # P(j tăng | i tăng)
            lift_up = both_up / ((p_up[i] * p_up[j]) + 1e-8) # Lift cùng tăng

            # Tính cho trường hợp CÙNG GIẢM
            both_down = (down[:, i] * down[:, j]).mean()
            conf_down = both_down / (p_down[i] + 1e-8)
            lift_down = both_down / ((p_down[i] * p_down[j]) + 1e-8)

            # Lấy giá trị lớn hơn giữa cùng tăng và cùng giảm
            support = max(both_up, both_down)
            confidence = max(conf_up, conf_down)
            lift = max(lift_up, lift_down)

            # Lọc: chỉ giữ cạnh thỏa đồng thời 3 điều kiện
            if support >= min_support and confidence >= min_confidence and lift >= lift_threshold:
                assoc_raw[i, j] = max(assoc_raw[i, j], float(lift))

    # Chuẩn hóa trọng số về [0, 1]
    max_val = assoc_raw.max()
    if max_val > 0:
        assoc_raw = assoc_raw / max_val

    np.fill_diagonal(assoc_raw, 1.0)
    assoc_raw = sparsify_keep_topk(assoc_raw, topk=topk, keep_self=True)

    debug_info = {
        "assoc_edges": int((assoc_raw > 0).sum() - N),
        "avg_p_up": float(p_up.mean()),
        "avg_p_down": float(p_down.mean())
    }

    return assoc_raw.astype(np.float32), debug_info


def build_combined_graph_from_train_window(return_2d, tickers, train_start_t, train_end_t):
    """
    Xây dựng đồ thị kết hợp từ Pearson Correlation + Association Rules.

    Quy trình kết hợp:
        1. Xây dựng đồ thị Pearson → pearson_raw [N, N]
        2. Xây dựng đồ thị Association → assoc_raw [N, N]
        3. Kết hợp: combined = max(pearson_raw, α × assoc_raw)
           với α = EXP_ASSOC_EDGE_WEIGHT = 0.50
        4. Giữ top-K=4 láng giềng cuối cùng
        5. Chuẩn hóa đối xứng: Â = D^{-1/2} · combined · D^{-1/2}

    Lý do dùng max() thay vì sum():
        max() ưu tiên cạnh mạnh nhất từ một trong hai nguồn.
        Nếu Pearson cho cạnh (i,j) = 0.85 nhưng Association cho 0.60,
        thì combined = max(0.85, 0.5*0.60) = 0.85.
        Điều này tránh "thổi phồng" trọng số khi hai phương pháp đồng thuận.

    Parameters
    ----------
    return_2d : np.ndarray [T, N]
        Ma trận return
    tickers : list of str
        Danh sách mã
    train_start_t, train_end_t : int
        Phạm vi training

    Returns
    -------
    adj_norm : np.ndarray [N, N]
        Ma trận kề kết hợp, đã chuẩn hóa đối xứng → đưa vào GCN
    combined_raw : np.ndarray [N, N]
        Ma trận kề thô (chưa chuẩn hóa) → để phân tích
    corr_raw : np.ndarray [N, N]
        Ma trận tương quan Pearson đầy đủ → để phân tích
    debug_info : dict
        Thống kê: số cạnh Pearson, Association, Combined
    """
    # Bước 1: Đồ thị Pearson
    pearson_raw, corr_raw = build_sparse_pearson_graph_from_train_window(
        return_2d=return_2d,
        train_start_t=train_start_t,
        train_end_t=train_end_t,
        recent_days=EXP_GRAPH_RECENT_DAYS,
        threshold=EXP_PEARSON_THRESHOLD,
        topk=EXP_PEARSON_TOPK
    )

    # Bước 2: Đồ thị Association Rule
    assoc_raw, assoc_debug = build_manual_association_graph_from_train_window(
        return_2d=return_2d,
        tickers=tickers,
        train_start_t=train_start_t,
        train_end_t=train_end_t,
        recent_days=EXP_ASSOC_RECENT_DAYS,
        min_support=EXP_ASSOC_MIN_SUPPORT,
        min_confidence=EXP_ASSOC_MIN_CONFIDENCE,
        lift_threshold=EXP_ASSOC_LIFT_THRESHOLD,
        topk=EXP_ASSOC_TOPK
    )

    # Bước 3: Kết hợp bằng element-wise max
    # combined[i,j] = max(pearson[i,j], α × assoc[i,j])
    combined_raw = np.maximum(pearson_raw, EXP_ASSOC_EDGE_WEIGHT * assoc_raw)

    # Bước 4: Giữ top-K cuối cùng (K=4)
    combined_raw = sparsify_keep_topk(combined_raw, topk=EXP_FINAL_GRAPH_TOPK, keep_self=True)

    # Bước 5: Chuẩn hóa đối xứng Â = D^{-1/2} A D^{-1/2}
    adj_norm = normalize_adjacency(combined_raw).astype(np.float32)

    debug_info = {
        "pearson_edges": int((pearson_raw > 0).sum() - len(tickers)),
        "assoc_edges": assoc_debug["assoc_edges"],
        "combined_edges": int((combined_raw > 0).sum() - len(tickers))
    }

    return adj_norm, combined_raw, corr_raw, debug_info
