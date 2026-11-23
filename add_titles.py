"""Adds the title lookup table used by qa.py to an existing wiki.db (also called by build_index.py).
ttl(tfold, title, tnorm, alen, disamb): tfold = fold(title) so queries typed without Turkish characters still match."""
import sqlite3, sys
from textnorm import fold

def add_titles(db):
    db.execute('DROP TABLE IF EXISTS ttl')
    db.execute('CREATE TABLE ttl(tfold TEXT, title TEXT, tnorm TEXT, alen INTEGER, disamb INTEGER)')
    n, rows = 0, []
    rd = db.cursor()
    for title, tnorm, alen, body in rd.execute('SELECT title, tnorm, alen, body FROM doc WHERE ord = 0'):
        dis = int('kastedilmiş olabilir' in body or 'anlam ayrımı' in title or 'anlamlara gelebilir' in body)
        rows.append((fold(title), title, tnorm, alen, dis))
        if len(rows) >= 5000:   # v4.2.1: batch, never hold every title in RAM (512 MB hosts)
            db.executemany('INSERT INTO ttl VALUES (?,?,?,?,?)', rows); n += len(rows); rows = []
    if rows:
        db.executemany('INSERT INTO ttl VALUES (?,?,?,?,?)', rows); n += len(rows)
    rows = n
    db.execute('CREATE INDEX ttl_f ON ttl(tfold)')
    db.commit()
    return rows

if __name__ == '__main__':
    c = sqlite3.connect(sys.argv[1] if len(sys.argv) > 1 else 'data/wiki.db')
    print(add_titles(c), 'titles')
