#!/usr/bin/env python3
"""Build data/wiki.db: a SQLite FTS5 (BM25) index over Turkish Wikipedia passages.

Input : one or more parquet files with columns title, url, text (e.g. data/wiki_tr_1.parquet)
Output: data/wiki.db  (table doc + contentless FTS5 table fts, rowid = doc.id)

Usage: python build_index.py data/wiki_tr_*.parquet [--out data/wiki.db] [--max-chars 4000]
"""
import argparse, os, re, sqlite3, sys, time
import pyarrow.parquet as pq
from textnorm import norm

STOP_SECTIONS = ('Kaynakça', 'Dış bağlantılar', 'Ayrıca bakınız', 'Notlar', 'Konuyla ilgili yayınlar', 'Kaynaklar')


def passages(text, max_chars, target=700):
    out, cur, used = [], '', 0
    for para in re.split(r'\n\s*\n', text):
        p = ' '.join(para.split())
        if not p:
            continue
        if p in STOP_SECTIONS or any(p.startswith(s) and len(p) < 40 for s in STOP_SECTIONS):
            break
        if len(p) < 40 and not p.endswith('.'):
            continue  # section heading
        if cur and len(cur) + len(p) > target:
            out.append(cur); cur = ''
        cur = (cur + ' ' + p).strip()
        used += len(p)
        if used >= max_chars:
            break
    if cur:
        out.append(cur)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('parquet', nargs='+')
    ap.add_argument('--out', default='data/wiki.db')
    ap.add_argument('--max-chars', type=int, default=15000, help='indexed characters per article (lead first)')
    ap.add_argument('--append', action='store_true', help='add to an unfinished <out>.tmp (multi-step builds)')
    ap.add_argument('--no-finalize', action='store_true', help='leave <out>.tmp unfinished (more --append runs follow)')
    a = ap.parse_args()
    tmp = a.out + '.tmp'
    if os.path.exists(tmp) and not a.append:
        os.remove(tmp)
    db = sqlite3.connect(tmp)
    db.executescript("""
      PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;
      CREATE TABLE IF NOT EXISTS doc(id INTEGER PRIMARY KEY, title TEXT, url TEXT, body TEXT, ord INTEGER, tnorm TEXT, alen INTEGER);
      CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(title, body, content='', tokenize='unicode61 remove_diacritics 2');
    """)
    t0, n_art = time.time(), 0
    n_doc = db.execute('SELECT COALESCE(MAX(id),0) FROM doc').fetchone()[0]
    for path in a.parquet:
        f = pq.ParquetFile(path)
        for g in range(f.num_row_groups):
            rows = f.read_row_group(g, columns=['title', 'url', 'text']).to_pylist()
            docs, ftsr = [], []
            for r in rows:
                title, text = (r['title'] or '').strip(), r['text'] or ''
                if not title or not text:
                    continue
                n_art += 1
                for i, p in enumerate(passages(text, a.max_chars)):
                    n_doc += 1
                    docs.append((n_doc, title, r['url'], p, i, norm(title), len(text)))
                    ftsr.append((n_doc, norm(title), norm(p)))
            db.executemany('INSERT INTO doc VALUES (?,?,?,?,?,?,?)', docs)
            db.executemany('INSERT INTO fts(rowid,title,body) VALUES (?,?,?)', ftsr)
            if g % 20 == 0:
                print(f'{path} group {g}/{f.num_row_groups}: {n_art} articles, {n_doc} passages, {time.time()-t0:.0f}s', flush=True)
            db.commit()
    if a.no_finalize:
        db.commit(); db.close(); print(f'partial: {n_art} articles added, {n_doc} passages total, {time.time()-t0:.0f}s'); return
    db.execute('CREATE INDEX IF NOT EXISTS doc_tnorm ON doc(tnorm, ord)')
    db.execute("INSERT INTO fts(fts) VALUES('optimize')")
    db.commit()
    from add_titles import add_titles   # folded title table used by qa.py
    print('titles', add_titles(db))
    db.close()
    os.replace(tmp, a.out)
    print(f'done: {n_art} articles, {n_doc} passages -> {a.out} ({os.path.getsize(a.out)/1e6:.0f} MB) in {time.time()-t0:.0f}s')


if __name__ == '__main__':
    main()
