import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from src.rolling_scaler import RollingMinMaxScaler
from src.models import HybridLSTMGNNGraphGate, TSNAttentionGraphGatedLSTMGNN


def load_checkpoint_generic(ckpt_path: Path):
    ckpt = torch.load(ckpt_path, map_location="cpu")

    if isinstance(ckpt, dict):
        if "state_dict" in ckpt:
            return ckpt["state_dict"], ckpt
        if "model_state_dict" in ckpt:
            return ckpt["model_state_dict"], ckpt

        tensor_like = all(hasattr(v, "shape") for v in ckpt.values())
        if tensor_like:
            return ckpt, {"raw_state_dict": True}

    raise ValueError(
        "Unsupported checkpoint format. Expected state_dict/model_state_dict or raw state_dict."
    )


def infer_model_dims_from_state_dict(state_dict: dict):
    try:
        seq_input_dim = state_dict["lstm.weight_ih_l0"].shape[1]
        lstm_hidden = state_dict["lstm.weight_ih_l0"].shape[0] // 4
        node_input_dim = state_dict["node_proj.weight"].shape[1]
        gnn_hidden = state_dict["node_proj.weight"].shape[0]
        # graph_head or mlp hidden shape
        if "mlp.0.weight" in state_dict:
            mlp_hidden = state_dict["mlp.0.weight"].shape[0]
        elif "graph_head.0.weight" in state_dict:
            mlp_hidden = state_dict["graph_head.0.weight"].shape[0]
        else:
            mlp_hidden = 64
        return {
            "seq_input_dim": int(seq_input_dim),
            "node_input_dim": int(node_input_dim),
            "lstm_hidden": int(lstm_hidden),
            "gnn_hidden": int(gnn_hidden),
            "mlp_hidden": int(mlp_hidden),
        }
    except Exception as e:
        raise RuntimeError(f"Could not infer model dims from checkpoint: {e}") from e


def load_npz_bundle(npz_path: Path):
    data = np.load(npz_path, allow_pickle=True)

    required = ["X_seq", "X_node", "A", "last_close"]
    for key in required:
        if key not in data:
            raise KeyError(f"Missing required key in npz bundle: {key}")

    x_seq = data["X_seq"]
    x_node = data["X_node"]
    adj = data["A"]
    last_close = data["last_close"]

    tickers = data["tickers"] if "tickers" in data else None
    as_of_date = data["as_of_date"].item() if "as_of_date" in data else None

    # chuẩn hóa shape về [B, N, ...]
    if x_seq.ndim == 3:
        x_seq = np.expand_dims(x_seq, axis=0)
    if x_node.ndim == 2:
        x_node = np.expand_dims(x_node, axis=0)
    if adj.ndim == 2:
        adj = np.expand_dims(adj, axis=0)
    if last_close.ndim == 1:
        last_close = np.expand_dims(last_close, axis=0)

    # Đọc thông số scaler để khôi phục
    scaler_params = {}
    for key in ["scaler_feature_mins", "scaler_feature_maxs", "scaler_close_mins", "scaler_close_maxs", "scaler_window_size"]:
        if key in data:
            scaler_params[key] = data[key]

    return {
        "X_seq": x_seq.astype(np.float32),
        "X_node": x_node.astype(np.float32),
        "A": adj.astype(np.float32),
        "last_close": last_close.astype(np.float32),
        "tickers": tickers.tolist() if tickers is not None else None,
        "as_of_date": as_of_date,
        "scaler_params": scaler_params
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True, help="Path to checkpoint .pt/.pth")
    parser.add_argument("--input-npz", required=True, help="Path to inference tensor bundle .npz")
    parser.add_argument(
        "--output-json",
        default="outputs/inference/latest_prediction.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--dropout",
        type=float,
        default=0.2,
        help="Dropout used when rebuilding model architecture",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        choices=["cpu", "cuda"],
        help="Inference device",
    )
    args = parser.parse_args()

    ckpt_path = Path(args.checkpoint)
    npz_path = Path(args.input_npz)
    out_path = Path(args.output_json)

    if not ckpt_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {ckpt_path}")
    if not npz_path.exists():
        raise FileNotFoundError(f"Input npz not found: {npz_path}")

    state_dict, ckpt_meta = load_checkpoint_generic(ckpt_path)
    dims = infer_model_dims_from_state_dict(state_dict)
    bundle = load_npz_bundle(npz_path)

    device = torch.device(
        "cuda" if args.device == "cuda" and torch.cuda.is_available() else "cpu"
    )

    is_tsn = "temporal_attention.W.weight" in state_dict

    if is_tsn:
        model = TSNAttentionGraphGatedLSTMGNN(
            seq_input_dim=dims["seq_input_dim"],
            node_input_dim=dims["node_input_dim"],
            lstm_hidden=dims["lstm_hidden"],
            gnn_hidden=dims["gnn_hidden"],
            mlp_hidden=dims["mlp_hidden"],
            dropout=args.dropout,
        ).to(device)
    else:
        model = HybridLSTMGNNGraphGate(
            seq_input_dim=dims["seq_input_dim"],
            node_input_dim=dims["node_input_dim"],
            lstm_hidden=dims["lstm_hidden"],
            gnn_hidden=dims["gnn_hidden"],
            mlp_hidden=dims["mlp_hidden"],
            dropout=args.dropout,
        ).to(device)

    model.load_state_dict(state_dict, strict=True)
    model.eval()

    x_seq = torch.tensor(bundle["X_seq"], dtype=torch.float32, device=device)
    x_node = torch.tensor(bundle["X_node"], dtype=torch.float32, device=device)
    adj = torch.tensor(bundle["A"], dtype=torch.float32, device=device)
    last_close = torch.tensor(bundle["last_close"], dtype=torch.float32, device=device)

    with torch.no_grad():
        pred_close, gate = model(x_seq, x_node, adj, last_close, return_gate=True)

    pred_close_np = pred_close.cpu().numpy()[0]  # [N] (scaled)
    gate_np = gate.cpu().numpy()[0]              # [N]
    last_close_np = bundle["last_close"][0]      # [N] (scaled)

    # Khôi phục scaler động để inverse transform
    has_scaler = len(bundle["scaler_params"]) > 0
    if has_scaler:
        scaler = RollingMinMaxScaler.from_npz_params(bundle["scaler_params"])
        # Inverse transform về giá trị thực
        pred_close_real = scaler.inverse_transform_close(pred_close_np)
        last_close_real = scaler.inverse_transform_close(last_close_np)
        print("[scaler] Khôi phục thành công Rolling MinMaxScaler. Đã thực hiện inverse transform.")
    else:
        # Fallback nếu không tìm thấy scaler trong npz
        pred_close_real = pred_close_np
        last_close_real = last_close_np
        print("[warn] Không tìm thấy Rolling MinMaxScaler params trong npz. Trả về scaled values.")

    tickers = bundle["tickers"]
    n_nodes = pred_close_np.shape[0]
    if tickers is None:
        tickers = [f"NODE_{i}" for i in range(n_nodes)]

    rows = []
    for i in range(n_nodes):
        last_val = float(last_close_real[i])
        pred_val = float(pred_close_real[i])
        pred_return = (pred_val - last_val) / abs(last_val) if abs(last_val) > 1e-12 else None

        rows.append(
            {
                "ticker": str(tickers[i]),
                "last_close": last_val,
                "pred_close": pred_val,
                "pred_return": pred_return,
                "graph_gate": float(gate_np[i]),
            }
        )

    result = {
        "checkpoint": str(ckpt_path),
        "input_npz": str(npz_path),
        "as_of_date": bundle["as_of_date"],
        "device": str(device),
        "model_dims": dims,
        "num_nodes": n_nodes,
        "predictions": rows,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("=" * 80)
    print("Inference completed successfully (Inverse transformed to real prices).")
    print(f"Output JSON: {out_path}")
    print(f"Num nodes: {n_nodes}")
    print("=" * 80)

    for row in rows[:10]:
        print(
            f"{row['ticker']:>8} | last_real={row['last_close']:.4f} | "
            f"pred_real={row['pred_close']:.4f} | pred_ret={row['pred_return']:.6%}"
        )


if __name__ == "__main__":
    main()
