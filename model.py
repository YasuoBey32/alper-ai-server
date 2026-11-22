# Alper AI beyni: sıfırdan yazılmış GPT tarzı transformer.
import math, torch, torch.nn as nn, torch.nn.functional as F

class Config:
    vocab = 8192; ctx = 256; d = 256; layers = 6; heads = 4

class Attn(nn.Module):
    def __init__(s, c):
        super().__init__(); s.h = c.heads
        s.qkv = nn.Linear(c.d, 3 * c.d); s.proj = nn.Linear(c.d, c.d)
    def forward(s, x):
        B, T, C = x.shape
        q, k, v = s.qkv(x).split(C, 2)
        q, k, v = [t.view(B, T, s.h, C // s.h).transpose(1, 2) for t in (q, k, v)]
        y = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        return s.proj(y.transpose(1, 2).contiguous().view(B, T, C))

class Block(nn.Module):
    def __init__(s, c):
        super().__init__()
        s.ln1 = nn.LayerNorm(c.d); s.att = Attn(c); s.ln2 = nn.LayerNorm(c.d)
        s.fc = nn.Linear(c.d, 4 * c.d); s.out = nn.Linear(4 * c.d, c.d)
    def forward(s, x):
        x = x + s.att(s.ln1(x))
        return x + s.out(F.gelu(s.fc(s.ln2(x)), approximate='tanh'))

class GPT(nn.Module):
    def __init__(s, c=Config()):
        super().__init__(); s.c = c
        s.tok = nn.Embedding(c.vocab, c.d); s.pos = nn.Embedding(c.ctx, c.d)
        s.blocks = nn.ModuleList([Block(c) for _ in range(c.layers)]); s.lnf = nn.LayerNorm(c.d)
        s.apply(s._init)
        for n, p in s.named_parameters():
            if n.endswith('proj.weight') or n.endswith('out.weight'):
                nn.init.normal_(p, 0, 0.02 / math.sqrt(2 * c.layers))
    def _init(s, m):
        if isinstance(m, (nn.Linear, nn.Embedding)): nn.init.normal_(m.weight, 0, 0.02)
        if isinstance(m, nn.Linear) and m.bias is not None: nn.init.zeros_(m.bias)
    def forward(s, idx, targets=None, mask=None):
        T = idx.shape[1]
        x = s.tok(idx) + s.pos(torch.arange(T))
        for b in s.blocks: x = b(x)
        logits = s.lnf(x) @ s.tok.weight.T  # bağlı ağırlıklar
        if targets is None: return logits
        l = F.cross_entropy(logits.view(-1, logits.size(-1)), targets.view(-1), reduction='none')
        if mask is not None: l = (l * mask.view(-1)).sum() / mask.sum().clamp(min=1)
        else: l = l.mean()
        return logits, l

@torch.no_grad()
def generate(m, ids, n=120, temp=0.8, topk=40, stop=None):
    m.eval()
    for _ in range(n):
        x = torch.tensor([ids[-m.c.ctx:]])
        lg = m(x)[0, -1] / temp
        v, _ = torch.topk(lg, topk); lg[lg < v[-1]] = -1e9
        nxt = torch.multinomial(F.softmax(lg, -1), 1).item()
        if nxt == stop: break
        ids.append(nxt)
    return ids
