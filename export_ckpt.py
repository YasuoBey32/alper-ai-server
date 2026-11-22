#!/usr/bin/env python3
"""Strip the optimizer state from a training checkpoint and store the config next to the weights.

python export_ckpt.py ../../ai/ckpt_sft.pt model/alper.pt
"""
import sys, torch
from lm import load_config

src, dst = sys.argv[1], sys.argv[2]
ck = torch.load(src, map_location='cpu', weights_only=False)
sd = ck['m'] if 'm' in ck else ck
c = load_config(ck, sd)
cfg = {k: getattr(c, k) for k in ('vocab', 'ctx', 'd', 'layers', 'heads')}
torch.save({'m': sd, 'cfg': cfg, 'step': ck.get('step')}, dst)
print('saved', dst, cfg)
