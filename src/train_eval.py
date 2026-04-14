# src/train_eval.py

import copy
import numpy as np
import torch
import torch.nn as nn

from sklearn.metrics import mean_squared_error, mean_absolute_error


def compute_metrics(y_true: np.ndarray,
                    y_pred: np.ndarray,
                    last_close: np.ndarray,
                    eps: float = 0.0):
    y_true_f = y_true.reshape(-1)
    y_pred_f = y_pred.reshape(-1)
    last_f = last_close.reshape(-1)

    mse = mean_squared_error(y_true_f, y_pred_f)
    mae = mean_absolute_error(y_true_f, y_pred_f)
    rmse = float(np.sqrt(mse))

    true_up = (y_true_f - last_f) > eps
    pred_up = (y_pred_f - last_f) > eps
    directional_accuracy = float((true_up == pred_up).mean())

    return {
        "MSE": float(mse),
        "MAE": float(mae),
        "RMSE": float(rmse),
        "Directional_Accuracy": directional_accuracy
    }


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
        loss = criterion(pred_close, y_close)
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
        loss = criterion(pred_close, y_close)
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
    best_val = float("inf")
    wait = 0

    history = {"train_loss": [], "val_loss": []}

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