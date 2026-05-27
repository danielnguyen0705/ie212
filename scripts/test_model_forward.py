# scripts/test_model_forward.py

import torch
import _path_setup

from src.models import LSTMOnlyModel, HybridLSTMGNNGraphGate
from src.config import LSTM_HIDDEN, GNN_HIDDEN, MLP_HIDDEN, DROPOUT, FEATURE_COLS


def main():
    B = 2
    N = 10
    T = 20
    F_seq = 1
    F_node = len(FEATURE_COLS)

    seq = torch.randn(B, N, T, F_seq)
    node_x = torch.randn(B, N, F_node)
    adj = torch.eye(N).unsqueeze(0).repeat(B, 1, 1)
    last_close = torch.randn(B, N)

    lstm_model = LSTMOnlyModel(
        input_dim=1,
        lstm_hidden=LSTM_HIDDEN,
        dropout=DROPOUT
    )

    hybrid_model = HybridLSTMGNNGraphGate(
        seq_input_dim=1,
        node_input_dim=F_node,
        lstm_hidden=LSTM_HIDDEN,
        gnn_hidden=GNN_HIDDEN,
        mlp_hidden=MLP_HIDDEN,
        dropout=DROPOUT
    )

    lstm_out = lstm_model(seq, node_x, adj, last_close)
    hybrid_out, gate = hybrid_model(seq, node_x, adj, last_close, return_gate=True)

    print("LSTM output shape:", lstm_out.shape)
    print("Hybrid output shape:", hybrid_out.shape)
    print("Gate shape:", gate.shape)


if __name__ == "__main__":
    main()
