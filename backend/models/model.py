import torch
import torch.nn as nn
import math

# ================= 全局配置 (必须保持不变) =================
HISTORY_LEN = 168
PRED_LEN = 24
IN_FEATURES = 10
HIDDEN_DIM = 128
NUM_LAYERS = 3
NUM_HEADS = 4
DROPOUT = 0.1


class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=5000):
        super(PositionalEncoding, self).__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer('pe', pe)

    def forward(self, x):
        return x + self.pe[:, :x.size(1), :]


class TransformerModel(nn.Module):
    def __init__(self):
        super(TransformerModel, self).__init__()
        # 1. 线性分支
        self.skip_linear = nn.Linear(HISTORY_LEN, PRED_LEN)

        # 2. Transformer 分支
        self.input_fc = nn.Linear(IN_FEATURES, HIDDEN_DIM)
        self.pos_encoder = PositionalEncoding(HIDDEN_DIM)
        encoder_layers = nn.TransformerEncoderLayer(d_model=HIDDEN_DIM, nhead=NUM_HEADS, dropout=DROPOUT,
                                                    batch_first=True)
        self.transformer_encoder = nn.TransformerEncoder(encoder_layers, num_layers=NUM_LAYERS)

        self.out_fc = nn.Sequential(
            nn.Linear(HIDDEN_DIM * HISTORY_LEN, 256),
            nn.ReLU(),
            nn.Dropout(DROPOUT),
            nn.Linear(256, PRED_LEN)
        )

    def forward(self, x):
        """
        x shape: (Batch, Time, Nodes, Features) -> (B, 168, N, 10)
        """
        B, T, N, F = x.shape

        # --- 路径 A: 线性残差 (Linear) ---
        # 提取负荷数据 (假设是第0维特征)
        x_load = x[..., 0].permute(0, 2, 1)  # (B, N, 168)
        linear_out = self.skip_linear(x_load)  # (B, N, 24)

        # --- 路径 B: Transformer ---
        # 变换维度以适应 Transformer: (Batch*Nodes, Time, Features)
        x_trans = x.permute(0, 2, 1, 3).reshape(B * N, T, F)  # (B*N, 168, 10)

        x_trans = self.input_fc(x_trans)  # (B*N, 168, 128)
        x_trans = self.pos_encoder(x_trans)  # (B*N, 168, 128)
        x_trans = self.transformer_encoder(x_trans)  # (B*N, 168, 128)

        # 展平并通过全连接层
        x_trans = x_trans.reshape(B * N, -1)  # (B*N, 168*128)
        trans_out = self.out_fc(x_trans)  # (B*N, 24)

        # 还原维度 (B, N, 24)
        trans_out = trans_out.reshape(B, N, -1)

        # --- 融合 ---
        final_out = (linear_out + trans_out).permute(0, 2, 1)  # (B, 24, N)

        # ⚠️ 关键修正：必须返回结果，且增加最后一个维度 (B, 24, N, 1)
        return final_out.unsqueeze(-1)