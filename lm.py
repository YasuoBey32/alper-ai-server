"""Alper Çekirdek, numpy-only inference (deploy build for small free hosts: no torch, ~40 MB RAM for the model).

Same network as model.py (GPT: tied embeddings, pre-LN blocks, causal attention, tanh-GELU) and the same sampling
rules as the torch lm.py (repetition penalty, temperature, top-k, stop tokens, loop guard). Weights come from
model/alper.npz (made from model/alper.pt by convert_npz.py); a KV cache keeps generation O(T) per token.
"""
import json, os, threading
import numpy as np
from tokenizers import Tokenizer

U, A, S = '<' + '|kullanici|>', '<' + '|asistan|>', '<' + '|son|>'   # v4.3: real special tokens (no zero-width char)


class Cfg:
    def __init__(self, d):
        self.vocab, self.ctx, self.d = int(d['vocab']), int(d['ctx']), int(d['d'])
        self.layers, self.heads = int(d['layers']), int(d['heads'])


def _ln(x, w, b, eps=1e-5):
    m = x.mean(-1, keepdims=True)
    v = ((x - m) ** 2).mean(-1, keepdims=True)
    return (x - m) / np.sqrt(v + eps) * w + b


def _gelu(x):
    return 0.5 * x * (1.0 + np.tanh(0.7978845608028654 * (x + 0.044715 * x ** 3)))


class NumpyGPT:
    def __init__(self, path):
        z = np.load(path)
        self.cfg = Cfg(json.loads(str(z['__cfg__'])))
        self.w = {k: z[k].astype(np.float32) for k in z.files if k != '__cfg__'}
        self.params = sum(v.size for v in self.w.values())

    def forward(self, ids, cache=None):
        """ids: new token ids (list). cache: list of (K, V) per layer, extended in place. Returns logits [T, vocab]."""
        c, w = self.cfg, self.w
        start = 0 if not cache else cache[0][0].shape[1]
        T = len(ids)
        x = w['tok.weight'][ids] + w['pos.weight'][start:start + T]
        H, hd = c.heads, c.d // c.heads
        for i in range(c.layers):
            p = f'blocks.{i}.'
            h = _ln(x, w[p + 'ln1.weight'], w[p + 'ln1.bias'])
            qkv = h @ w[p + 'att.qkv.weight'].T + w[p + 'att.qkv.bias']
            q, k, v = np.split(qkv, 3, axis=-1)
            q = q.reshape(T, H, hd).transpose(1, 0, 2)
            k = k.reshape(T, H, hd).transpose(1, 0, 2)
            v = v.reshape(T, H, hd).transpose(1, 0, 2)
            if cache is not None:
                if len(cache) > i:
                    k = np.concatenate([cache[i][0], k], 1); v = np.concatenate([cache[i][1], v], 1)
                    cache[i] = (k, v)
                else:
                    cache.append((k, v))
            L = k.shape[1]
            att = (q @ k.transpose(0, 2, 1)) / np.sqrt(hd)
            qpos = np.arange(start, start + T)[:, None]
            att = np.where(np.arange(L)[None, :] <= qpos, att, -np.inf)
            att = np.exp(att - att.max(-1, keepdims=True))
            att /= att.sum(-1, keepdims=True)
            y = (att @ v).transpose(1, 0, 2).reshape(T, c.d)
            x = x + y @ w[p + 'att.proj.weight'].T + w[p + 'att.proj.bias']
            h = _ln(x, w[p + 'ln2.weight'], w[p + 'ln2.bias'])
            h = _gelu(h @ w[p + 'fc.weight'].T + w[p + 'fc.bias'])
            x = x + h @ w[p + 'out.weight'].T + w[p + 'out.bias']
        return _ln(x, w['lnf.weight'], w['lnf.bias']) @ w['tok.weight'].T


class AlperLM:
    def __init__(self, ckpt_path, tok_path):
        npz = os.path.splitext(ckpt_path)[0] + '.npz'
        self.m = NumpyGPT(npz)
        self.cfg = self.m.cfg
        self.params = self.m.params
        self.tok = Tokenizer.from_file(tok_path)
        self.stop_ids = {self.tok.token_to_id(S), self.tok.token_to_id(U)}
        self.lock = threading.Lock()
        self.rng = np.random.default_rng()

    def prompt_ids(self, turns, max_new):
        txt = ''.join(U + u + A + ((b + S) if b is not None else '') for u, b in turns)
        ids = self.tok.encode(txt).ids
        room = self.cfg.ctx - max_new
        if len(ids) > room:
            ids = [self.tok.token_to_id(U)] + ids[len(ids) - room + 1:]
        return ids

    def stream(self, turns, temp=0.7, topk=30, max_new=160, rep=1.15, cancel=None):
        with self.lock:
            ids = self.prompt_ids(turns, max_new)
            out, sent, cache = [], '', []
            lg_all = self.m.forward(ids, cache)
            for _ in range(max_new):
                if cancel is not None and cancel.is_set():
                    break
                lg = lg_all[-1].astype(np.float64).copy()
                for t in set(out[-40:]):
                    lg[t] = lg[t] / rep if lg[t] > 0 else lg[t] * rep
                lg = lg / max(temp, 1e-3)
                kth = np.partition(lg, -topk)[-topk]
                lg[lg < kth] = -1e9
                pr = np.exp(lg - lg.max()); pr /= pr.sum()
                nxt = int(self.rng.choice(len(pr), p=pr))
                if nxt in self.stop_ids:
                    break
                ids.append(nxt); out.append(nxt)
                if len(ids) >= self.cfg.ctx:
                    break
                lg_all = self.m.forward([nxt], cache)
                txt = self.tok.decode(out)
                if txt.endswith('\ufffd'):
                    continue
                tail = txt[-20:]
                if len(txt) > 60 and len(tail) == 20 and txt[:-20].find(tail) >= 0:
                    break
                if len(txt) > len(sent):
                    yield txt[len(sent):]
                    sent = txt
