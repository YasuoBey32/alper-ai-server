"""Download the big files (our own model + our Wikipedia index) from the public HF dataset repo.
ALPER_DATA_REPO (default Yasuo850k/alper-ai-data), ALPER_DATA_REV (default main). Skips files already present."""
import os, shutil, sys, time, urllib.request
REPO = os.environ.get('ALPER_DATA_REPO', 'Yasuo850k/alper-ai-data')
REV = os.environ.get('ALPER_DATA_REV', 'main')
FILES = [('alper.npz', 'model/alper.npz'), ('tokenizer.json', 'model/tokenizer.json'), ('wiki.db', 'data/wiki.db')]
for name, dst in FILES:
    if os.path.exists(dst) and os.path.getsize(dst) > 0 and '--force' not in sys.argv:
        continue
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    url = f'https://huggingface.co/datasets/{REPO}/resolve/{REV}/{name}'
    t = time.time()
    with urllib.request.urlopen(url, timeout=120) as r, open(dst + '.part', 'wb') as f:
        shutil.copyfileobj(r, f, 1 << 22)
    os.replace(dst + '.part', dst)
    print(f'{dst}: {os.path.getsize(dst)/1e6:.0f} MB in {time.time()-t:.0f}s', flush=True)
