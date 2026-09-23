"""PyTorch implementation of the GA-optimized GAT-TCN-LSTM hybrid model."""

import torch
import torch.nn as nn
import torch.nn.functional as F

class GATLayer(nn.Module):
    def __init__(self, in_features=6, out_features=96, heads=4):
        super().__init__()
        self.heads = heads
        self.out_features = out_features
        self.head_dim = out_features // heads
        
        self.W = nn.Linear(in_features, out_features, bias=False)
        self.attention = nn.Parameter(torch.zeros(heads, 2 * self.head_dim))
        
    def forward(self, nodes):
        B, S, N, _ = nodes.shape
        
        h = self.W(nodes) 
        h = h.view(B, S, N, self.heads, self.head_dim)
        
        h0, h1 = h[:, :, 0, :, :], h[:, :, 1, :, :]
        
        a00 = torch.cat([h0, h0], dim=-1)
        a01 = torch.cat([h0, h1], dim=-1)
        a10 = torch.cat([h1, h0], dim=-1)
        a11 = torch.cat([h1, h1], dim=-1)
        
        e00 = F.leaky_relu((a00 * self.attention).sum(-1), negative_slope=0.2)
        e01 = F.leaky_relu((a01 * self.attention).sum(-1), negative_slope=0.2)
        e10 = F.leaky_relu((a10 * self.attention).sum(-1), negative_slope=0.2)
        e11 = F.leaky_relu((a11 * self.attention).sum(-1), negative_slope=0.2)
        
        alpha0 = F.softmax(torch.stack([e00, e01], dim=-1), dim=-1)
        alpha1 = F.softmax(torch.stack([e10, e11], dim=-1), dim=-1)
        
        o0 = alpha0[..., 0].unsqueeze(-1) * h0 + alpha0[..., 1].unsqueeze(-1) * h1
        o1 = alpha1[..., 0].unsqueeze(-1) * h0 + alpha1[..., 1].unsqueeze(-1) * h1
        
        o0 = F.elu(o0.reshape(B, S, self.out_features))
        o1 = F.elu(o1.reshape(B, S, self.out_features))
        
        out = torch.cat([o0, o1], dim=-1)
        return out


class GAT_TCN_LSTM(nn.Module):
    def __init__(self):
        super().__init__()
        
        self.gat = GATLayer(in_features=6, out_features=96, heads=4)
        
        self.tcn1 = nn.Conv1d(192, 128, kernel_size=3, padding=1, dilation=1)
        self.tcn2 = nn.Conv1d(128, 128, kernel_size=3, padding=2, dilation=2)
        self.tcn3 = nn.Conv1d(128, 128, kernel_size=3, padding=4, dilation=4)
        
        self.lstm = nn.LSTM(128, 64, num_layers=2, batch_first=True)
        
        self.fc = nn.Sequential(
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Dropout(0.05),
            nn.Linear(64, 10)
        )

    def forward(self, x):
        # x shape: (batch_size, 24, 7)
        # feature mapping assumed exactly:
        # [node_1_soil, node_2_soil, temp, hum, rain, wind, solar]
        
        # We form 2 nodes, each having its own soil moisture + the 5 shared weather variables
        n1 = x[:, :, [0, 2, 3, 4, 5, 6]]
        n2 = x[:, :, [1, 2, 3, 4, 5, 6]]
        nodes = torch.stack([n1, n2], dim=2)
        
        gat_out = self.gat(nodes) # (B, S, 192)
        
        # TCN expects (batch, channels, seq_len)
        tcn_in = gat_out.transpose(1, 2)
        
        t1 = F.relu(self.tcn1(tcn_in))
        t2 = F.relu(self.tcn2(t1))
        t3 = F.relu(self.tcn3(t2))
        
        # LSTM expects (batch, seq_len, features)
        lstm_in = t3.transpose(1, 2)
        out, _ = self.lstm(lstm_in)
        
        # take the last timestep
        out = out[:, -1, :]
        return self.fc(out)
