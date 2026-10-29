import torch
import torch.nn as nn
import torch.nn.functional as F

class RMSNorm(nn.Module):
    def __init__(self, d, eps=1e-5):
        super().__init__()
        self.g = nn.Parameter(torch.ones(d))
        self.eps = eps
    def forward(self, x):
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps) * self.g

class SwiGLU(nn.Module):
    def __init__(self, d):
        super().__init__()
        h = int(d * 4 * 2 / 3)
        self.w1 = nn.Linear(d, h, bias=False)
        self.w2 = nn.Linear(d, h, bias=False)
        self.w3 = nn.Linear(h, d, bias=False)
    def forward(self, x):
        return self.w3(F.silu(self.w1(x)) * self.w2(x))

class Block(nn.Module):
    def __init__(self, d, h):
        super().__init__()
        self.n1 = RMSNorm(d)
        self.n2 = RMSNorm(d)
        self.attn = nn.MultiheadAttention(d, h, batch_first=True)
        self.ff = SwiGLU(d)
    def forward(self, x):
        T = x.shape[1]
        mask = torch.triu(torch.full((T, T), float('-inf')), diagonal=1)
        a, _ = self.attn(self.n1(x), self.n1(x), self.n1(x), attn_mask=mask, need_weights=False)
        x = x + a
        x = x + self.ff(self.n2(x))
        return x

class AxiomLLM(nn.Module):
    def __init__(self, vocab_size, d=128, h=4, L=4, T=32):
        super().__init__()
        self.T = T
        self.emb = nn.Embedding(vocab_size, d)
        self.pos = nn.Embedding(T, d)
        self.blocks = nn.ModuleList([Block(d, h) for _ in range(L)])
        self.norm = RMSNorm(d)
        self.head = nn.Linear(d, vocab_size, bias=False)
    def forward(self, idx):
        B, T = idx.shape
        x = self.emb(idx) + self.pos(torch.arange(T))
        for b in self.blocks:
            x = b(x)
        return self.head(self.norm(x))
