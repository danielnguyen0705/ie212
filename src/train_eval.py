# src/train_eval.py

import copy
import numpy as np
import torch
import torch.nn as nn

from sklearn.metrics import mean_squared_error, mean_absolute_error
from src.evaluation import compute_full_evaluation


def compute_metrics(y_true: np.ndarray,
                    y_pred: np.ndarray,
                    last_close: np.ndarray,
                    eps: float = 0.0):
    """
    Tính toán các chỉ số đánh giá bằng cách tích hợp module evaluation toàn diện.
    y_true, y_pred, last_close có shape: [num_samples, num_stocks]
    """
    # Nếu là 1D (đã flatten), ta đưa về shape [N, 1] hoặc giữ nguyên
    if y_true.ndim == 1:
        # Giả sử đây là batch dẹt, đưa về 2D để tương thích
        y_true_2d = y_true.reshape(-1, 1)
        y_pred_2d = y_pred.reshape(-1, 1)
        last_2d = last_close.reshape(-1, 1)
    else:
        y_true_2d = y_true
        y_pred_2d = y_pred
        last_2d = last_close

    # Gọi hàm tính toán toàn diện trong src/evaluation.py
    eval_dict = compute_full_evaluation(
        y_true=y_true_2d,
        y_pred=y_pred_2d,
        last_close=last_2d,
        risk_free_rate=0.0,
        direction_eps=eps
    )

    # Đảm bảo các key truyền thống (MSE, MAE, RMSE, Directional_Accuracy) tồn tại
    # để không làm gãy các code gọi cũ
    eval_dict["MSE"] = eval_dict["MSE"]
    eval_dict["MAE"] = eval_dict["MAE"]
    eval_dict["RMSE"] = eval_dict["RMSE"]
    eval_dict["Directional_Accuracy"] = eval_dict["Directional_Accuracy"]

    return eval_dict


def compute_model_loss(model, pred_close, y_close, last_close, eps=0.0):
    mse_loss = nn.functional.mse_loss(pred_close, y_close)

    direction_weight = float(getattr(model, "direction_loss_weight", 0.0))
    if direction_weight <= 0:
        return mse_loss

    logit_scale = float(getattr(model, "direction_logit_scale", 50.0))
    direction_target = (y_close - last_close > eps).float()
    direction_logits = (pred_close - last_close) * logit_scale
    direction_loss = nn.functional.binary_cross_entropy_with_logits(
        direction_logits,
        direction_target
    )

    return mse_loss + direction_weight * direction_loss


def train_one_epoch(model, loader, optimizer, criterion, device):
    model.train()
    total_loss = 0.0

    for batch in loader:
        if len(batch) == 6:
            seq, node_x, adj, y_res, y_close, last_close = batch
        elif len(batch) == 5:
            seq, node_x, adj, y_close, last_close = batch
        else:
            raise ValueError("Unexpected batch format in train_one_epoch.")

        seq = seq.to(device)
        node_x = node_x.to(device)
        adj = adj.to(device)
        y_close = y_close.to(device)
        last_close = last_close.to(device)

        optimizer.zero_grad()
        pred_close = model(seq, node_x, adj, last_close)
        loss = compute_model_loss(model, pred_close, y_close, last_close)
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * y_close.size(0)

    return total_loss / len(loader.dataset)


@torch.no_grad()
def evaluate_loss(model, loader, criterion, device):
    model.eval()
    total_loss = 0.0

    for batch in loader:
        if len(batch) == 6:
            seq, node_x, adj, y_res, y_close, last_close = batch
        elif len(batch) == 5:
            seq, node_x, adj, y_close, last_close = batch
        else:
            raise ValueError("Unexpected batch format in evaluate_loss.")

        seq = seq.to(device)
        node_x = node_x.to(device)
        adj = adj.to(device)
        y_close = y_close.to(device)
        last_close = last_close.to(device)

        pred_close = model(seq, node_x, adj, last_close)
        loss = compute_model_loss(model, pred_close, y_close, last_close)
        total_loss += loss.item() * y_close.size(0)

    return total_loss / len(loader.dataset)


@torch.no_grad()
def predict_model(model, loader, device):
    model.eval()

    preds = []
    trues = []
    lasts = []

    for batch in loader:
        if len(batch) == 6:
            seq, node_x, adj, y_res, y_close, last_close = batch
        elif len(batch) == 5:
            seq, node_x, adj, y_close, last_close = batch
        else:
            raise ValueError("Unexpected batch format in predict_model.")

        seq = seq.to(device)
        node_x = node_x.to(device)
        adj = adj.to(device)
        last_close_device = last_close.to(device)

        pred_close = model(seq, node_x, adj, last_close_device)

        preds.append(pred_close.cpu().numpy())
        trues.append(y_close.numpy())
        lasts.append(last_close.numpy())

    preds = np.concatenate(preds, axis=0)
    trues = np.concatenate(trues, axis=0)
    lasts = np.concatenate(lasts, axis=0)

    return preds, trues, lasts


def fit_model_silent(model, train_loader, val_loader, epochs, lr, patience, device, verbose=False):
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=lr)

    best_state = None
    best_val = evaluate_loss(model, val_loader, criterion, device)
    wait = 0

    history = {"train_loss": [], "val_loss": [], "initial_val_loss": best_val}

    for epoch in range(1, epochs + 1):
        train_loss = train_one_epoch(model, train_loader, optimizer, criterion, device)
        val_loss = evaluate_loss(model, val_loader, criterion, device)

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)

        if verbose:
            print(f"Epoch {epoch:02d} | train_loss={train_loss:.6f} | val_loss={val_loss:.6f}")

        if val_loss < best_val:
            best_val = val_loss
            best_state = copy.deepcopy(model.state_dict())
            wait = 0
        else:
            wait += 1
            if wait >= patience:
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    return model, history


@torch.no_grad()
def predict_model_graph_gate(model, loader, device):
    model.eval()

    preds = []
    trues = []
    lasts = []
    gates = []

    for batch in loader:
        if len(batch) == 6:
            seq, node_x, adj, _, y_close, last_close = batch
        elif len(batch) == 5:
            seq, node_x, adj, y_close, last_close = batch
        else:
            raise ValueError("Unexpected batch format in predict_model_graph_gate.")

        seq = seq.to(device)
        node_x = node_x.to(device)
        adj = adj.to(device)
        last_close_device = last_close.to(device)

        pred_close, gate = model(seq, node_x, adj, last_close_device, return_gate=True)

        preds.append(pred_close.cpu().numpy())
        trues.append(y_close.numpy())
        lasts.append(last_close.numpy())
        gates.append(gate.cpu().numpy())

    preds = np.concatenate(preds, axis=0)
    trues = np.concatenate(trues, axis=0)
    lasts = np.concatenate(lasts, axis=0)
    gates = np.concatenate(gates, axis=0)

    return preds, trues, lasts, gates


def initialize_hybrid_from_lstm_model(hybrid_model, lstm_model):
    """
    Sao chép trọng số phần LSTM từ lstm_model sang hybrid_model
    để hybrid_model có điểm khởi đầu tốt.
    """
    hybrid_state = hybrid_model.state_dict()
    lstm_state = lstm_model.state_dict()

    for k, v in lstm_state.items():
        if k in hybrid_state and v.shape == hybrid_state[k].shape:
            hybrid_state[k] = copy.deepcopy(v)

    hybrid_model.load_state_dict(hybrid_state)
    return hybrid_model


def initialize_graph_gate_from_no_gate(gate_model, no_gate_model):
    """
    Sao chép toàn bộ trọng số từ no_gate_model sang gate_model.
    """
    gate_state = gate_model.state_dict()
    no_gate_state = no_gate_model.state_dict()

    for k, v in no_gate_state.items():
        if k in gate_state and v.shape == gate_state[k].shape:
            gate_state[k] = copy.deepcopy(v)

    gate_model.load_state_dict(gate_state)
    return gate_model