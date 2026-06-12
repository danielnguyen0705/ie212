# src/models.py

import torch
import torch.nn as nn


class SimpleGCNLayer(nn.Module):
    def __init__(self, in_dim: int, out_dim: int):
        super().__init__()
        self.linear = nn.Linear(in_dim, out_dim)

    def forward(self, x: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        h = self.linear(x)
        out = torch.bmm(adj, h)
        return out


class LSTMOnlyModel(nn.Module):
    def __init__(self, input_dim=1, lstm_hidden=64, dropout=0.2):
        super().__init__()

        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=lstm_hidden,
            num_layers=1,
            batch_first=True
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(lstm_hidden, 1)

    def forward(self, seq, node_x, adj, last_close):
        B, N, T, F = seq.shape
        seq_flat = seq.reshape(B * N, T, F)

        out, _ = self.lstm(seq_flat)
        h = out[:, -1, :]
        h = self.dropout(h)

        pred_res = self.fc(h).reshape(B, N)
        pred_close = last_close + pred_res
        return pred_close


class HybridLSTMGNNNoGate(nn.Module):
    def __init__(self, seq_input_dim, node_input_dim,
                 lstm_hidden=64, gnn_hidden=32, mlp_hidden=64, dropout=0.2):
        super().__init__()

        self.lstm = nn.LSTM(
            input_size=seq_input_dim,
            hidden_size=lstm_hidden,
            num_layers=1,
            batch_first=True
        )

        self.node_proj = nn.Linear(node_input_dim, gnn_hidden)
        self.gcn1 = SimpleGCNLayer(gnn_hidden, gnn_hidden)
        self.gcn2 = SimpleGCNLayer(gnn_hidden, gnn_hidden)

        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)

        self.mlp = nn.Sequential(
            nn.Linear(lstm_hidden + gnn_hidden, mlp_hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(mlp_hidden, 1)
        )

    def forward(self, seq, node_x, adj, last_close, return_gate=False):
        B, N, T, F = seq.shape

        seq_flat = seq.reshape(B * N, T, F)
        lstm_out, _ = self.lstm(seq_flat)
        h = lstm_out[:, -1, :].reshape(B, N, -1)
        h = self.dropout(h)

        g = self.node_proj(node_x)
        g = self.gcn1(g, adj)
        g = self.relu(g)
        g = self.dropout(g)

        g = self.gcn2(g, adj)
        g = self.relu(g)
        g = self.dropout(g)

        fusion = torch.cat([h, g], dim=-1)

        pred_res = self.mlp(fusion).squeeze(-1)
        pred_close = last_close + pred_res

        if return_gate:
            no_gate_marker = torch.ones(B, N, device=g.device, dtype=g.dtype)
            return pred_close, no_gate_marker

        return pred_close


class HybridLSTMGNNGraphGate(nn.Module):
    def __init__(self, seq_input_dim, node_input_dim,
                 lstm_hidden=64, gnn_hidden=32, mlp_hidden=64, dropout=0.2,
                 gate_type="sigmoid"):
        super().__init__()

        self.gate_type = gate_type
        self.lstm = nn.LSTM(
            input_size=seq_input_dim,
            hidden_size=lstm_hidden,
            num_layers=1,
            batch_first=True
        )

        self.node_proj = nn.Linear(node_input_dim, gnn_hidden)
        self.gcn1 = SimpleGCNLayer(gnn_hidden, gnn_hidden)
        self.gcn2 = SimpleGCNLayer(gnn_hidden, gnn_hidden)

        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)

        self.gate_layer = nn.Linear(lstm_hidden + gnn_hidden, 1)
        nn.init.zeros_(self.gate_layer.weight)
        if gate_type == "sigmoid":
            nn.init.constant_(self.gate_layer.bias, -0.5)
        else:
            nn.init.zeros_(self.gate_layer.bias)

        self.mlp = nn.Sequential(
            nn.Linear(lstm_hidden + gnn_hidden, mlp_hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(mlp_hidden, 1)
        )

    def forward(self, seq, node_x, adj, last_close, return_gate=False):
        B, N, T, F = seq.shape

        seq_flat = seq.reshape(B * N, T, F)
        lstm_out, _ = self.lstm(seq_flat)
        h = lstm_out[:, -1, :].reshape(B, N, -1)
        h = self.dropout(h)

        g = self.node_proj(node_x)
        g = self.gcn1(g, adj)
        g = self.relu(g)
        g = self.dropout(g)

        g = self.gcn2(g, adj)
        g = self.relu(g)
        g = self.dropout(g)

        gate_input = torch.cat([h, g], dim=-1)
        if self.gate_type == "sigmoid":
            gate = torch.sigmoid(self.gate_layer(gate_input))
        else:
            gate = 1.0 + 0.5 * torch.tanh(self.gate_layer(gate_input))

        g_gated = gate * g
        fusion = torch.cat([h, g_gated], dim=-1)

        pred_res = self.mlp(fusion).squeeze(-1)
        pred_close = last_close + pred_res

        if return_gate:
            return pred_close, gate.squeeze(-1)

        return pred_close


class TemporalAttention(nn.Module):
    def __init__(self, hidden_dim):
        super().__init__()
        self.W = nn.Linear(hidden_dim, hidden_dim)
        self.V = nn.Linear(hidden_dim, 1, bias=False)

    def forward(self, lstm_out):
        scores = self.V(torch.tanh(self.W(lstm_out)))
        weights = torch.softmax(scores, dim=1)
        context = torch.sum(weights * lstm_out, dim=1)
        return context, weights.squeeze(-1)


class TSNAttentionGraphGatedLSTMGNN(nn.Module):
    def __init__(self, seq_input_dim, node_input_dim,
                 lstm_hidden=64, gnn_hidden=32, mlp_hidden=64, dropout=0.2,
                 gate_type="sigmoid"):
        super().__init__()

        self.gate_type = gate_type
        self.lstm = nn.LSTM(
            input_size=seq_input_dim,
            hidden_size=lstm_hidden,
            num_layers=1,
            batch_first=True
        )

        self.temporal_attention = TemporalAttention(lstm_hidden)

        self.node_proj = nn.Linear(node_input_dim, gnn_hidden)
        self.gcn1 = SimpleGCNLayer(gnn_hidden, gnn_hidden)
        self.gcn2 = SimpleGCNLayer(gnn_hidden, gnn_hidden)

        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)

        self.gate_layer = nn.Linear(lstm_hidden + gnn_hidden, 1)
        nn.init.zeros_(self.gate_layer.weight)
        if gate_type == "sigmoid":
            nn.init.constant_(self.gate_layer.bias, -0.5)
        else:
            nn.init.zeros_(self.gate_layer.bias)

        self.mlp = nn.Sequential(
            nn.Linear(lstm_hidden + gnn_hidden, mlp_hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(mlp_hidden, 1)
        )

    def forward(self, seq, node_x, adj, last_close, return_gate=False, return_attention=False):
        B, N, T, F = seq.shape

        seq_flat = seq.reshape(B * N, T, F)
        lstm_out, _ = self.lstm(seq_flat)
        h_context, attn_weights = self.temporal_attention(lstm_out)
        h = h_context.reshape(B, N, -1)
        attn_weights = attn_weights.reshape(B, N, T)
        h = self.dropout(h)

        g = self.node_proj(node_x)
        g = self.gcn1(g, adj)
        g = self.relu(g)
        g = self.dropout(g)

        g = self.gcn2(g, adj)
        g = self.relu(g)
        g = self.dropout(g)

        gate_input = torch.cat([h, g], dim=-1)
        if self.gate_type == "sigmoid":
            gate = torch.sigmoid(self.gate_layer(gate_input))
        else:
            gate = 1.0 + 0.5 * torch.tanh(self.gate_layer(gate_input))

        g_gated = gate * g
        fusion = torch.cat([h, g_gated], dim=-1)

        pred_res = self.mlp(fusion).squeeze(-1)
        pred_close = last_close + pred_res

        if return_attention:
            return pred_close, gate.squeeze(-1), attn_weights
        if return_gate:
            return pred_close, gate.squeeze(-1)

        return pred_close