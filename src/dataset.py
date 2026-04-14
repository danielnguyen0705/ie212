# src/dataset.py

import torch
from torch.utils.data import Dataset


class StockGraphDataset(Dataset):
    def __init__(self, X_seq, X_node, A, y_res, y_close, last_close):
        self.X_seq = torch.tensor(X_seq, dtype=torch.float32)
        self.X_node = torch.tensor(X_node, dtype=torch.float32)
        self.A = torch.tensor(A, dtype=torch.float32)
        self.y_res = torch.tensor(y_res, dtype=torch.float32)
        self.y_close = torch.tensor(y_close, dtype=torch.float32)
        self.last_close = torch.tensor(last_close, dtype=torch.float32)

    def __len__(self):
        return len(self.y_close)

    def __getitem__(self, idx):
        return (
            self.X_seq[idx],
            self.X_node[idx],
            self.A[idx],
            self.y_res[idx],
            self.y_close[idx],
            self.last_close[idx]
        )