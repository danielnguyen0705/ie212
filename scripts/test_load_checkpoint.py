# scripts/test_load_checkpoint.py

import torch
import _path_setup

from src.config import FEATURE_COLS, LSTM_HIDDEN, GNN_HIDDEN, MLP_HIDDEN, DROPOUT
from src.models import LSTMOnlyModel, HybridLSTMGNNGraphGate
from src.artifacts import load_model_checkpoint


def main():
    device = "cpu"

    lstm_model = LSTMOnlyModel(
        input_dim=1,
        lstm_hidden=LSTM_HIDDEN,
        dropout=DROPOUT
    )

    hybrid_model = HybridLSTMGNNGraphGate(
        seq_input_dim=1,
        node_input_dim=len(FEATURE_COLS),
        lstm_hidden=LSTM_HIDDEN,
        gnn_hidden=GNN_HIDDEN,
        mlp_hidden=MLP_HIDDEN,
        dropout=DROPOUT
    )

    lstm_model, lstm_meta = load_model_checkpoint(
        lstm_model,
        "models/lstm_expanding_best_full.pt",
        map_location=device
    )

    hybrid_model, hybrid_meta = load_model_checkpoint(
        hybrid_model,
        "models/hybrid_expanding_best_full.pt",
        map_location=device
    )

    print("Loaded LSTM checkpoint.")
    print(lstm_meta)

    print("\nLoaded Hybrid checkpoint.")
    print(hybrid_meta)


if __name__ == "__main__":
    main()
