"""model/alper.pt (torch) -> model/alper.npz (numpy) for the torch-free deploy build. Needs torch only here."""
import json, sys, numpy as np, torch
src, dst = sys.argv[1], sys.argv[2]
ck = torch.load(src, map_location='cpu', weights_only=False)
sd = ck['m'] if isinstance(ck, dict) and 'm' in ck else ck
cfg = ck.get('cfg') if isinstance(ck, dict) else None
if not cfg:
    v, d = sd['tok.weight'].shape
    cfg = {'vocab': v, 'd': d, 'ctx': sd['pos.weight'].shape[0], 'heads': 4,
           'layers': 1 + max(int(k.split('.')[1]) for k in sd if k.startswith('blocks.'))}
arr = {k: t.detach().float().numpy() for k, t in sd.items()}
np.savez(dst, __cfg__=np.array(json.dumps(cfg)), **arr)
print('wrote', dst, cfg)
