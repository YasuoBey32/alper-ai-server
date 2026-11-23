"""qa.QA index backed by the server's SQLite FTS5 database (data/wiki.db, see build_index.py + add_titles.py)."""
import sqlite3, threading


class SqliteIndex:
    def __init__(self, path):
        self.path = path
        self.local = threading.local()

    def db(self):
        c = getattr(self.local, 'c', None)
        if c is None:
            c = sqlite3.connect(f'file:{self.path}?mode=ro', uri=True, check_same_thread=False)
            # v4.2.1: keep SQLite's own memory small on the 512 MB free host
            c.execute('PRAGMA cache_size=-8000')   # 8 MB page cache
            c.execute('PRAGMA mmap_size=0')
            c.execute('PRAGMA temp_store=FILE')
            self.local.c = c
        return c

    def titles(self, tfold):
        return self.db().execute('SELECT title, alen, disamb FROM ttl WHERE tfold = ?', (tfold,)).fetchall()

    def titles_prefix(self, prefix, n):
        return self.db().execute('SELECT title, tfold, alen, disamb FROM ttl WHERE tfold >= ? AND tfold < ? ORDER BY alen DESC LIMIT ?',
                                 (prefix, prefix + '\uffff', n)).fetchall()

    def _doc(self, r):
        b = r[3]
        return {'id': r[0], 'title': r[1], 'url': r[2], 'body': b, 'ord': r[4], 'alen': r[5],
                'disamb': r[4] == 0 and ('kastedilmiş olabilir' in b or 'anlamlara gelebilir' in b or 'anlam ayrımı' in r[1])}

    def lead(self, title):
        r = self.db().execute('SELECT id, title, url, body, ord, alen FROM doc WHERE title = ? AND ord = 0 LIMIT 1', (title,)).fetchone()
        return self._doc(r) if r else None

    def passages(self, title, n):
        return [self._doc(r) for r in self.db().execute(
            'SELECT id, title, url, body, ord, alen FROM doc WHERE title = ? ORDER BY ord LIMIT ?', (title, n))]

    def search(self, groups, n, lead_only, order='bm25'):
        parts = []
        for g in groups:
            alts = [('"%s"*' % t if pre and len(t) >= 3 else '"%s"' % t) for t, pre in g if t]
            if alts:
                parts.append('(' + ' OR '.join(alts) + ')')
        if not parts:
            return []
        sql = ('SELECT d.id, d.title, d.url, d.body, d.ord, d.alen FROM fts JOIN doc d ON d.id = fts.rowid WHERE fts MATCH ? '
               + ('AND d.ord = 0 ' if lead_only else '') + ('ORDER BY d.alen DESC' if order == 'alen' else 'ORDER BY bm25(fts, 8.0, 1.0)') + ' LIMIT ?')
        try:
            return [self._doc(r) for r in self.db().execute(sql, (' AND '.join(parts), n))]
        except sqlite3.OperationalError:
            return []
