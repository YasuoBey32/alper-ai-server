"""Alper Çekirdek: our own from-scratch GPT (model.py + tokenizer.json), used only for open-ended chat.

The checkpoint may grow later: the config is read from ckpt['cfg'] when present, otherwise inferred from tensor shapes.
"""
import os, threading, torch, torch.nn.functional as F
from tokenizers import Tokenizer
from model import GPT, Config

U, A, S = '<' + '|kullanici|>', '<' + '|asistan|>', '<' + '|son|>'   # v4.3: real special tokens (no zero-width char)


def load_config(ckpt, sd):
    c = Config()
    cfg = ckpt.get('cfg') if isinstance(ckpt, dict) else None
    if isinstance(cfg, dict):
        for k, v in cfg.items():
            setattr(c, k, v)
        return c
    c.vocab, c.d = sd['tok.weight'].shape
    c.ctx = sd['pos.weight'].shape[0]
    c.layers = 1 + max(int(k.split('.')[1]) for k in sd if k.startswith('blocks.'))
    c.heads = int(os.environ.get('ALPER_HEADS', c.heads))
    return c


class AlperLM:
    def __init__(self, ckpt_path, tok_path):
        torch.set_num_threads(int(os.environ.get('TORCH_THREADS', '2')))
        ck = torch.load(ckpt_path, map_location='cpu', weights_only=False)
        sd = ck['m'] if isinstance(ck, dict) and 'm' in ck else ck
        self.cfg = load_config(ck if isinstance(ck, dict) else {}, sd)
        self.m = GPT(self.cfg)
        self.m.load_state_dict(sd)
        self.m.eval()
        self.tok = Tokenizer.from_file(tok_path)
        self.stop_ids = {self.tok.token_to_id(S), self.tok.token_to_id(U)}
        self.lock = threading.Lock()
        self.params = sum(p.numel() for p in self.m.parameters())

    def prompt_ids(self, turns, max_new):
        """turns: [(user, bot_or_None)] -> token ids in the training chat format, trimmed from the left."""
        txt = ''.join(U + u + A + ((b + S) if b is not None else '') for u, b in turns)
        ids = self.tok.encode(txt).ids
        room = self.cfg.ctx - max_new
        if len(ids) > room:
            ids = [self.tok.token_to_id(U)] + ids[len(ids) - room + 1:]
        return ids

    @torch.no_grad()
    def stream(self, turns, temp=0.7, topk=30, max_new=160, rep=1.15, cancel=None):
        """Yields decoded text deltas."""
        with self.lock:
            ids = self.prompt_ids(turns, max_new)
            out, sent = [], ''
            for _ in range(max_new):
                if cancel is not None and cancel.is_set():
                    break
                x = torch.tensor([ids[-self.cfg.ctx:]])
                lg = self.m(x)[0, -1].clone()
                for t in set(out[-40:]):
                    lg[t] = lg[t] / rep if lg[t] > 0 else lg[t] * rep
                lg = lg / max(temp, 1e-3)
                v, _ = torch.topk(lg, topk)
                lg[lg < v[-1]] = -1e9
                nxt = int(torch.multinomial(F.softmax(lg, -1), 1))
                if nxt in self.stop_ids:
                    break
                ids.append(nxt); out.append(nxt)
                txt = self.tok.decode(out)
                if txt.endswith('\ufffd'):
                    continue  # incomplete UTF-8 byte sequence
                tail = txt[-20:]
                if len(txt) > 60 and len(tail) == 20 and txt[:-20].find(tail) >= 0:
                    break  # the small model started looping
                if len(txt) > len(sent):
                    yield txt[len(sent):]
                    sent = txt
