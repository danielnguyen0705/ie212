# src/graph_builder.py

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
    Symmetric normalization: D^{-1/2} A D^{-1/2}
    adj: [N, N]
    """
    adj = adj.astype(np.float32)
    deg = adj.sum(axis=1)
    deg_inv_sqrt = np.power(np.maximum(deg, 1e-8), -0.5)
    D_inv_sqrt = np.diag(deg_inv_sqrt)
    adj_norm = D_inv_sqrt @ adj @ D_inv_sqrt
    return adj_norm.astype(np.float32)


def sparsify_keep_topk(weight_mat, topk, keep_self=True):
    N = weight_mat.shape[0]
    out = np.zeros_like(weight_mat, dtype=np.float32)

    for i in range(N):
        row = weight_mat[i].copy()
        row[i] = 0.0

        pos_idx = np.where(row > 0)[0]
        if len(pos_idx) > 0:
            chosen = pos_idx[np.argsort(row[pos_idx])[::-1][:topk]]
            out[i, chosen] = row[chosen]

    out = np.maximum(out, out.T)

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
    graph_start_t = max(train_start_t, train_end_t - recent_days + 1)
    train_returns = return_2d[graph_start_t:train_end_t + 1].copy()

    corr = np.corrcoef(train_returns.T)
    corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)

    pearson_raw = np.abs(corr).astype(np.float32)
    pearson_raw[pearson_raw < threshold] = 0.0
    np.fill_diagonal(pearson_raw, 1.0)

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
    graph_start_t = max(train_start_t, train_end_t - recent_days + 1)
    train_returns = return_2d[graph_start_t:train_end_t + 1].copy()

    up = (train_returns > 0).astype(np.float32)
    down = (train_returns < 0).astype(np.float32)

    _, N = up.shape
    assoc_raw = np.zeros((N, N), dtype=np.float32)

    p_up = up.mean(axis=0)
    p_down = down.mean(axis=0)

    for i in range(N):
        for j in range(N):
            if i == j:
                continue

            both_up = (up[:, i] * up[:, j]).mean()
            conf_up = both_up / (p_up[i] + 1e-8)
            lift_up = both_up / ((p_up[i] * p_up[j]) + 1e-8)

            both_down = (down[:, i] * down[:, j]).mean()
            conf_down = both_down / (p_down[i] + 1e-8)
            lift_down = both_down / ((p_down[i] * p_down[j]) + 1e-8)

            support = max(both_up, both_down)
            confidence = max(conf_up, conf_down)
            lift = max(lift_up, lift_down)

            if support >= min_support and confidence >= min_confidence and lift >= lift_threshold:
                assoc_raw[i, j] = max(assoc_raw[i, j], float(lift))

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
    pearson_raw, corr_raw = build_sparse_pearson_graph_from_train_window(
        return_2d=return_2d,
        train_start_t=train_start_t,
        train_end_t=train_end_t,
        recent_days=EXP_GRAPH_RECENT_DAYS,
        threshold=EXP_PEARSON_THRESHOLD,
        topk=EXP_PEARSON_TOPK
    )

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

    combined_raw = np.maximum(pearson_raw, EXP_ASSOC_EDGE_WEIGHT * assoc_raw)
    combined_raw = sparsify_keep_topk(combined_raw, topk=EXP_FINAL_GRAPH_TOPK, keep_self=True)

    adj_norm = normalize_adjacency(combined_raw).astype(np.float32)

    debug_info = {
        "pearson_edges": int((pearson_raw > 0).sum() - len(tickers)),
        "assoc_edges": assoc_debug["assoc_edges"],
        "combined_edges": int((combined_raw > 0).sum() - len(tickers))
    }

    return adj_norm, combined_raw, corr_raw, debug_info