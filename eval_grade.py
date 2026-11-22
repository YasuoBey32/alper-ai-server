"""Graded eval: python eval_grade.py [data/wiki.db] [--lm]  -> table of correct / unsure / wrong.

eval_set.json: {"q", "ok": [accepted substrings]} for factual questions, "type": "chat" for templates /
free text, "type": "unanswerable" where the only right answer is "Bundan emin değilim".
A confident answer that contains none of the accepted substrings counts as WRONG (review by hand).
"""
import json, sys, time, os
from brain import Brain
from sqlite_index import SqliteIndex
from qa import QA
from textnorm import fold

here = os.path.dirname(os.path.abspath(__file__))
db = next((a for a in sys.argv[1:] if not a.startswith('--')), 'data/wiki.db')
lm = None
if '--lm' in sys.argv:
    from lm import AlperLM
    lm = AlperLM(os.path.join(here, 'model/alper.pt'), os.path.join(here, 'model/tokenizer.json'))
if db.endswith('.aoi'):
    sys.path.insert(0, os.path.join(here, '..', 'offline'))
    from aoi import AoiIndex
    br = Brain(QA(AoiIndex(db)), lm)
else:
    br = Brain(QA(SqliteIndex(db)), lm)
items = json.load(open(os.path.join(here, 'eval_set.json'), encoding='utf-8'))


def grade(it, kind, text):
    t = it.get('type', 'fact')
    if t == 'chat':
        return 'correct' if kind in ('smalltalk', 'identity', 'time', 'math', 'lm') else ('unsure' if kind == 'unsure' else 'wrong')
    if t == 'unanswerable':
        return 'correct' if kind == 'unsure' else 'wrong'
    if kind == 'unsure':
        return 'unsure'
    body = fold(text)
    return 'correct' if any(fold(k) in body for k in it['ok']) else 'wrong'


rows, tally = [], {}
for it in items:
    t0 = time.time()
    a = br.answer([{'role': 'user', 'content': it['q']}])
    text = a.text if a.stream is None else ''.join(a.stream(None)) + a.text
    g = grade(it, a.kind, text)
    grp = 'new' if it.get('new') else 'orig'
    tally.setdefault(grp, {'correct': 0, 'unsure': 0, 'wrong': 0})[g] += 1
    rows.append((grp, g, a.kind, it['q'], ' '.join(text.split())[:260], (time.time() - t0) * 1000))
for grp, g, kind, q, text, ms in rows:
    print(f'{"!!" if g == "wrong" else "  "} [{grp}] {g:7s} [{kind}] {q} ({ms:.0f} ms)\n      {text}')
print()
for grp, d in tally.items():
    print(grp, d)
tot = {k: sum(d[k] for d in tally.values()) for k in ('correct', 'unsure', 'wrong')}
print('total', tot)
