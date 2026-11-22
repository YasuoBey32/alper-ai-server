"""Our own retrieval: BM25 (SQLite FTS5) over Turkish Wikipedia + extractive answer selection.

No language model chooses facts: the answer text is copied verbatim from the best matching sentence(s).
Confidence is sentence-level: a passage only counts when one sentence (with the article title as context)
contains every required query term. Otherwise the caller must answer "Bundan emin değilim".
"""
import math, re, sqlite3, threading
from textnorm import norm, fold

STOP = set(norm(w) for w in """
ne neler nedir nelerdir kim kimdir kimler kimin kime kaç kaçtır kaçta nerede neresi neresidir nereden nereye nasıl
niye neden niçin hangi hangisi hangisidir mi mı mu mü midir mıdır mudur müdür misin mısın miydi ve veya ile ya da de ki
bir bu şu o bunu şunu onu bana sana bize hakkında bilgi ver verir verebilir misin anlat anlatır söyle söyler lütfen
acaba peki zaman için olan olarak gibi daha çok kadar var yok kısaca detaylı ayrıntılı açıkla
tanımı demek anlamı nerededir yerde
the a an of is are was what who where when which how why in on at to for about tell me please
""".split())

# words that help ranking but are not required to appear (verbs / measure words / time words)
WEAK = set(fold(w) for w in """
oldu olur olmustur olmus bitti biter basladi baslar yapildi yapilmistir dogdu dogmus oldu oldugu oldukleri
yilda yili yil yilinda tarihi tarihinde gun gunu ayinda en buyuk kucuk uzun yuksek yuksekligi uzunlugu
uzakligi derinligi nufusu alani metre km kilometre kac toplam genel resmi bugun simdi guncel
""".split())

DEF_CUES = ('nedir', 'kimdir', 'ne demek', 'anlami', 'tanimi', 'hakkinda', 'who is', 'what is')
NUM_CUES = ('kac', 'ne zaman', 'hangi yil', 'tarih', 'nufus', 'yuksekli', 'uzunlu', 'uzakli', 'when', 'how many', 'yilinda', 'dogdu', 'oldu', 'bitti')

SENT_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9"“(])')
QUOTE = re.compile(r"[’'`]")


def content_terms(q):
    """[(surface word, folded word, is_proper, is_weak)] for the query's content words."""
    out = []
    for raw in re.findall(r"[^\s,.;:!?()\"“”]+", q):
        w = QUOTE.split(raw)[0]
        f = re.sub(r'[^0-9a-z]', '', fold(w))
        if len(f) < 2 or norm(w) in STOP:
            continue
        proper = w[:1].isupper() and len(out) + 1 > 0 and not raw.isupper()
        out.append((w, f, proper, f in WEAK))
    # the first word of a sentence is capitalised anyway: treat it as proper only if it had a suffix apostrophe
    if out and q.strip()[:1].isupper():
        first_raw = re.findall(r"[^\s,.;:!?()\"“”]+", q.strip())[0]
        w, f, p, wk = out[0]
        if fold(QUOTE.split(first_raw)[0]) == f and not QUOTE.search(first_raw):
            out[0] = (w, f, f in _COMMON_PROPER or len(f) >= 3 and p, wk)
    return out


_COMMON_PROPER = set()


def possessive_pairs(q):
    """("Türkiye'nin başkenti") -> [('turkiye', 'baskenti')]: genitive noun followed by its head noun."""
    out = []
    for m in re.finditer(r"([A-Za-zÇĞİÖŞÜçğıöşü]+)[’'](?:n?[ıiuü]n)\b", q):
        a = fold(m.group(1))
        rest = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]+", q[m.end():])[:3]
        for w in rest:
            if norm(w) in STOP or norm(w) == 'en':
                continue
            if len(w) >= 3:
                out.append((a, fold(w)))
            break
    return out


def superlatives(q):
    return [fold(m.group(1)) for m in re.finditer(r"\ben\s+([a-zçğıöşü]{3,})", q, re.I) if norm(m.group(1)) not in STOP]


GEN = {'nin', 'nun', 'in', 'un', 'n'}


def near(sf, a, b, gap=4):
    """a (exact prefix, a proper noun) occurs at most `gap` words before stem(b), with no other possessor between."""
    toks = re.findall(r'[0-9a-z]+', sf)
    sb = stem(b)
    ia = [i for i, t in enumerate(toks) if t.startswith(a)]
    ib = [i for i, t in enumerate(toks) if t.startswith(sb)]
    for i in ia:
        for j in ib:
            if not 0 < j - i <= gap:
                continue
            mid = toks[i + 1:j]
            if mid and mid[0] in GEN:
                mid = mid[1:]
            if any(t in GEN for t in mid):
                continue  # "Japonya, Avustralya'nın başkenti" -> another possessor in between
            return True
    return False


QECHO = re.compile(r'(\?|\b(neresi|neresidir|nedir|kimdir|nerede|hangisidir|ne zaman|nelerdir)\b)')


def stem(f, proper=False):
    if f.isdigit() or proper:
        return f
    if len(f) >= 8:
        return f[:max(6, len(f) - 3)]
    if len(f) >= 6:
        return f[:len(f) - 1]
    return f


def has(text_folded, f, proper=False):
    if len(f) <= 3 and not f.isdigit():
        return re.search(r'\b' + re.escape(f) + r'\b', text_folded) is not None
    return re.search(r'\b' + re.escape(stem(f, proper)), text_folded) is not None


def split_sentences(text):
    """Sentence split that does not cut after abbreviations such as "d.", "ö.", "M.Ö.", "II.", "Dr."."""
    out = []
    for part in SENT_SPLIT.split(text):
        if out and re.search(r'(\b\w{1,2}|\b[IVXLC]+|\b(Dr|Prof|Doç|vb|vs|bkz|yy|St))\.$', out[-1]):
            out[-1] += ' ' + part
        else:
            out.append(part)
    return out


def sentences(text):
    return [s.strip() for s in split_sentences(text)
            if len(s.strip()) > 25 and 'Ayrıca bakınız' not in s and 'Ana madde' not in s]


class WikiIndex:
    def __init__(self, path):
        self.path = path
        self.local = threading.local()

    def db(self):
        c = getattr(self.local, 'c', None)
        if c is None:
            c = sqlite3.connect(f'file:{self.path}?mode=ro', uri=True, check_same_thread=False)
            self.local.c = c
        return c

    # ---- candidate generation
    def _fts(self, terms, limit, op):
        parts = []
        for _, f, p, _wk in terms:
            st = stem(f, p)
            parts.append(f'"{st}"*' if len(st) >= 3 and not st.isdigit() else f'"{st}"')
        if not parts:
            return []
        sql = ('SELECT d.id, d.title, d.url, d.body, d.ord FROM fts JOIN doc d ON d.id = fts.rowid '
               'WHERE fts MATCH ? ORDER BY bm25(fts, 8.0, 1.0) LIMIT ?')
        return self.db().execute(sql, (op.join(parts), limit)).fetchall()

    def _article(self, tn, limit=40):
        return self.db().execute('SELECT id, title, url, body, ord FROM doc WHERE tnorm = ? ORDER BY ord LIMIT ?',
                                 (tn, limit)).fetchall()

    def _title_hits(self, terms):
        db = self.db()
        ents = [t for t in terms if not t[3]] or terms
        ws, raws = [t[0] for t in ents], [t[0] for t in ents]
        found = []
        for n in range(min(4, len(ws)), 0, -1):
            for i in range(0, len(ws) - n + 1):
                t = norm(' '.join(ws[i:i + n]))
                for (tn,) in db.execute("SELECT DISTINCT tnorm FROM doc WHERE tnorm = ? OR (tnorm >= ? AND tnorm < ?) LIMIT 12",
                                        (t, t + ' (', t + ' )')):
                    found.append(tn)
            if found and n >= 2:
                break
        if len(ents) <= 3:  # titles containing all entity words ("Atatürk" -> "Mustafa Kemal Atatürk")
            q = ' AND '.join(f'"{fold(w)}"' for w in ws if len(fold(w)) >= 3)
            if q:
                for tn, cnt in db.execute("SELECT d.tnorm, MAX(d.alen) n FROM fts JOIN doc d ON d.id = fts.rowid "
                                          "WHERE fts MATCH ? GROUP BY d.tnorm ORDER BY n DESC LIMIT 5", ('title: (' + q + ')',)):
                    if cnt >= 3000:
                        found.append(tn)
        out, seen = [], set()
        for tn in found:
            if tn not in seen:
                seen.add(tn)
                out.append(tn)
        return out

    def _size(self, tn):
        return self.db().execute('SELECT MAX(alen) FROM doc WHERE tnorm = ?', (tn,)).fetchone()[0] or 0

    # ---- scoring
    def search(self, q, k=3):
        terms = content_terms(q)
        if not terms:
            return {'confident': False, 'passages': [], 'terms': []}
        req = [t for t in terms if not t[3]] or terms
        qf = fold(q)
        want_def = any(c in qf for c in DEF_CUES) or len(req) == 1 and len(terms) == 1
        want_num = any(c in qf for c in NUM_CUES)

        poss = possessive_pairs(q)
        sup = superlatives(q)
        cands = {}
        for tn in self._title_hits(terms):
            for r in self._article(tn):
                cands[r[0]] = (r, 1.5)
        rows = (self._fts(terms, 40, ' AND ') if len(terms) > 1 else []) + self._fts(req, 30, ' AND ') + self._fts(terms, 20, ' OR ')
        for rank, r in enumerate(rows):
            if r[0] not in cands:
                cands[r[0]] = (r, 0.8)

        sizes, scored = {}, []
        for r, prior in cands.values():
            title, body, ordn = r[1], r[3], r[4]
            tf = fold(title)
            tn = norm(title)
            if tn not in sizes:
                sizes[tn] = self._size(tn)
            title_req = sum(1 for t in req if has(tf, t[1], t[2]))
            best = (-1, 0, None)
            sl = sentences(body)
            if not sl:
                continue
            for i, s in enumerate(sl):
                sf = fold(s)
                win = sf + ' ' + (fold(sl[i + 1]) if i + 1 < len(sl) else '')
                cov_req = sum(1 for t in req if has(tf, t[1], t[2]) or has(sf, t[1], t[2])) / len(req)
                if poss and not all(near(sf, a, b) or (tf.startswith(a) and re.search(
                        r'\b(ulkenin|ulkesinin|sehrin|kentin|ilin)\s+' + re.escape(stem(b)), sf))
                        for a, b in poss):
                    cov_req = min(cov_req, 0.5)  # "X'in Y" asked: X and Y must be close together in this sentence
                if sup and (not all(re.search(r'\ben ' + re.escape(stem(a)), sf) for a in sup)
                            or re.search(r'\ben [a-z]+ (\d+|[a-z]*(inci|unci|nci|ncu)\b)', sf)
                            or re.search(r'(inci|unci|nci|ncu|\d\.) en ', sf)
                            or not any(near(sf, 'en ' + stem(a), t[1], 3) or re.search(r'\ben ' + re.escape(stem(a)) + r'[a-z]*( [a-z]+){0,2} ' + re.escape(stem(t[1])), sf)
                                       for a in sup for t in req if not t[2])):
                    cov_req = min(cov_req, 0.5)
                cov_all = sum(1 for t in terms if has(tf, t[1], t[2]) or has(win, t[1], t[2])) / len(terms)
                sc = 3 * cov_req + cov_all + (0.6 if want_num and re.search(r'\d', s) else 0) + (0.8 if i == 0 and ordn == 0 and want_def else 0)
                if sc > best[0]:
                    best = (sc, cov_req, i)
            disamb = 'kastedilmiş olabilir' in body or 'anlam ayrımı' in title or 'anlamlara gelebilir' in body
            plain_title = fold(re.sub(r'\(.*?\)', '', title))
            tw = re.findall(r'[0-9a-z]+', plain_title)
            pos = [j for j, w in enumerate(tw) if any(w.startswith(stem(t[1], t[2])) for t in terms)]
            extra_after = len([j for j in range(len(tw)) if pos and j > max(pos)]) if pos else len(tw)
            extra_before = len([j for j in range(len(tw)) if pos and j < min(pos)]) if pos else 0
            s = (prior + best[0] + 1.2 * (title_req / len(req)) + 0.45 * math.log(1 + sizes[tn] / 1000.0)
                 - (0.35 if want_def else 0.08) * ordn - 0.9 * extra_after - 0.25 * extra_before - (5 if disamb else 0)
                 - (0.8 if '(' in title and not all(any(has(qf, w) for w in re.findall(r'[0-9a-z]{3,}', fold(m))) for m in re.findall(r'\((.*?)\)', title)) else 0))
            scored.append((s, best[1], title_req, best[2], r, disamb))
        scored.sort(key=lambda x: -x[0])
        top = scored[:k]
        confident = False
        if top:
            s, cov, th, si, r, disamb = top[0]
            # every required term must co-occur in one sentence (title counts as context), and
            # single-entity questions need the entity in the article title
            confident = cov >= 1.0 and not disamb and (th > 0 or len(req) >= 2)
        return {
            'confident': confident,
            'terms': [t[1] for t in terms],
            'req': [t[1] for t in req],
            'want_def': want_def, 'want_num': want_num,
            'passages': [{'title': r[1], 'url': r[2], 'text': r[3], 'ord': r[4], 'score': round(s, 2),
                          'coverage': round(c, 2), 'title_hits': th, 'sent': si} for s, c, th, si, r, d in top],
        }


def best_sentences(question, passage, result, max_sent=2, max_chars=480):
    """Pick the answer sentence(s) verbatim from the passage."""
    text = passage['text']
    sl = sentences(text) or [text]
    tf = fold(passage['title'])
    terms = [(None, f, False, f in WEAK) for f in result.get('terms', [])]
    want_num, want_def = result.get('want_num'), result.get('want_def')
    sc = []
    for i, s in enumerate(sl):
        sf = fold(s)
        hit = sum(1 for t in terms if has(sf, t[1]) or has(tf, t[1]))
        v = hit + (0.8 if want_num and re.search(r'\d', s) else 0) + (1.5 if i == 0 and passage['ord'] == 0 and want_def else 0) - 0.04 * i
        sc.append((v, i))
    sc.sort(key=lambda x: -x[0])
    chosen = sorted({sc[0][1]} | ({sc[1][1]} if len(sc) > 1 and sc[1][0] >= sc[0][0] - 0.5 and max_sent > 1 else set()))
    out = ''
    for i in chosen:
        if out and len(out) + len(sl[i]) > max_chars:
            break
        out += (' ' if out else '') + sl[i]
    out = re.sub(r'\s*\(\s*[;,]?\s*\)', '', out)  # empty "( )" left by the dump
    return out[:max_chars + 200]


def score_external(question, sources):
    """Rank snippets the app sent (live web / Wikipedia API) with the same sentence-level rules as the index.

    Returns [(coverage, source, best_sentence)] sorted by coverage; the best sentence is what gets quoted.
    """
    terms = content_terms(question)
    req = [t for t in terms if not t[3]] or terms
    poss, sup = possessive_pairs(question), superlatives(question)
    out = []
    for s in sources or []:
        if not req:
            break
        tf = fold(s.get('title', ''))
        snip = ' '.join((s.get('snippet') or '').split())
        snip = re.sub(r'^\d{1,2} \w{3,8}\.? \d{4} · ', '', snip)  # "31 Ara 2020 · " date prefix
        sl = [x.strip() for x in split_sentences(snip) if len(x.strip()) > 15] or ([snip] if snip else [])
        best = (0.0, '')
        for x in sl:
            sf = fold(x)
            if QECHO.search(sf):
                continue  # the snippet just repeats the question
            cov = sum(1 for t in req if has(sf, t[1], t[2]) or has(tf, t[1], t[2])) / len(req)
            if poss and not all(near(sf, a, b) for a, b in poss):
                cov = min(cov, 0.5)
            if sup and not all(re.search(r'\ben ' + re.escape(stem(a)), sf) for a in sup):
                cov = min(cov, 0.5)
            if cov > best[0]:
                best = (cov, x)
        out.append((best[0], s, best[1]))
    # ties: encyclopedic sources first, then the order the app sent them in
    order = {id(x[1]): i for i, x in enumerate(out)}
    out.sort(key=lambda x: (-x[0], 0 if str(x[1].get('origin', '')).startswith('wikipedia') else 1,
                            1 if re.search(r'\b(once|eskiden|onceden)\b', fold(x[2])) else 0, order[id(x[1])]))
    return out
