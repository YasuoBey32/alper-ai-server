"""Alper AI grounded question answering (shared logic; mirrored 1:1 in the app's OfflineQA.java).

No model picks facts. Every confident answer is a sentence copied verbatim from a Wikipedia lead/passage.
Pipeline for a factual question:
  1. relation  "X'in başkenti / para birimi / en büyük gezegeni neresi|nedir|hangisidir"
               -> votes from lead sentences "T, X'in R(dir)" (answer T) and "X'in R Z" (answer Z)
  2. entity    the longest span of the question that is an article title (or an alias in a lead sentence)
               -> definition: first lead sentence; otherwise a sentence of that article holding every remaining
                  required word plus the type the question wants (a year for "ne zaman", a place for "nerede"…)
  3. otherwise -> "Bundan emin değilim."
The index is abstract (see Index protocol below): SQLite FTS5 on the server, our compact binary index on the phone.
"""
import re
from textnorm import fold

# ------------------------------------------------------------------ words
STOP = set(fold(w) for w in """
ne neler nedir nelerdir kim kimdir kimdi kimler kimin kime kaç kaçtır kaçta nerede nerededir neresi neresidir nereden
nereye neresinde nasıl niye neden niçin hangi hangisi hangisidir mi mı mu mü midir mıdır mudur müdür misin mısın miydi
ve veya ile ya da de ki bir bu o bunu onu bana sana bize hakkında bilgi ver verir verebilir anlat anlatır söyle
söyler lütfen acaba peki zaman için olan olarak gibi daha çok kadar var yok kısaca detaylı ayrıntılı açıkla tanımı demek
demektir anlamı yerde etti eder etmiştir edildi yaptı yapmıştır oldu olur olmuştur olmuş eden
the a an of is are was what who where when which how why in on at to for about tell me please
""".split())

WEAK = set(fold(w) for w in """
bitti biter basladi baslar yapildi yapilmistir dogdu dogmus oldugu olduklari yilda yili yil yilinda tarihi tarihinde
gun gunu ayinda en buyuk kucuk uzun yuksek yuksekligi uzunlugu uzakligi derinligi nufusu alani metre km kilometre kac
toplam genel resmi bugun simdi guncel derece derecede yazdi yapti buldu kurdu
""".split())

WH_END = {'neresi', 'neresidir', 'nedir', 'kimdir', 'kim', 'hangisidir', 'hangisi', 'ne', 'nelerdir', 'kimdi'}
MEASURE = ('nufus', 'yuzolcum', 'yukseklig', 'uzunlug', 'alan', 'derinlig', 'uzaklig', 'cap', 'agirlig', 'sicaklig',
           'hiz', 'yas', 'sayi', 'boy', 'kutle', 'yogunlug', 'genislig', 'rakim')
BLOCK_MOD = {'eski', 'ilk', 'onceki', 'gecici', 'kultur', 'kis', 'yaz', 'yeni', 'fiili', 'ikinci', 'ucuncu', 'son',
             'zamanki', 'tarihi', 'dini', 'ekonomik', 'ticari', 'gayriresmi'}
BLOCK_BEFORE_X = {'zamanlar', 'zamanki', 'eskiden', 'onceden', 'zaman', 'donemde', 'doneminde', 'iken'}
ORDINAL = re.compile(r'^(\d+|ikinci|ucuncu|dorduncu|besinci|altinci|yedinci|sekizinci|dokuzuncu|onuncu)$')
GEN = {'nin', 'nun', 'in', 'un', 'n'}
CONNECT = {'da', 'de', 've', 'van', 'von', 'bin', 'ibn', 'el', 'al', 'of'}   # inside names: Leonardo da Vinci, Romeo ve Juliet
ORD_WORDS = {'birinci': 'i.', 'ikinci': 'ii.', 'ucuncu': 'iii.', 'dorduncu': 'iv.'}

TOK = re.compile(r"[0-9A-Za-zÇĞİÖŞÜçğıöşüÂâÎîÛûÉéÀ-ÖØ-öø-ÿ]+")
QUOTE = re.compile(r"[’'`]")
SENT_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9"“(])')
MONTHS = ('ocak', 'subat', 'mart', 'nisan', 'mayis', 'haziran', 'temmuz', 'agustos', 'eylul', 'ekim', 'kasim', 'aralik')
WHERE_CUE = re.compile(r"\b(bulunan|bulunur|bulunmaktadir|yer alan|yer alir|yer almaktadir|konumlu|kiyisinda|sinirlari"
                       r"|ilinde|ilcesinde|bolgesinde|kitasinda|ulkesinde|kentinde|sehrinde|eyaletinde|illeri)\b")
YEAR = re.compile(r'\b(1\d{3}|20\d{2}|\d{1,3}0?)\b')

JUNK = re.compile(r"\{\{|\}\}|\s\|\s|bakınız|karıştırılmamalıdır|Ayrıca bakınız|Ana madde")
TEMPORAL_Q = re.compile(r"\d|\b(eski|eskiden|once|onceki|onceden|ilk|gecmiste|zamaninda|doneminde|iken)\b")
NOUN_SUF = ['larinin', 'lerinin', 'larini', 'lerini', 'larin', 'lerin', 'lari', 'leri', 'sinin', 'sunun', 'sini', 'sunu',
            'yini', 'yunu', 'inin', 'unun', 'ini', 'unu', 'nin', 'nun', 'dir', 'tir', 'dur', 'tur', 'si', 'su', 'yi', 'yu',
            'ni', 'nu', 'in', 'un', 'de', 'da', 'te', 'ta', 'i', 'u']
VERB_SUF = ['mistir', 'mustur', 'misti', 'mustu', 'mis', 'mus', 'madi', 'medi', 'di', 'du', 'ti', 'tu', 'ar', 'er', 'ir', 'ur']


def toks(s):
    return [fold(t) for t in TOK.findall(s)]


def stem(f, proper=False, verb=False):
    if proper or f.isdigit() or len(f) <= 4:
        return f
    if verb:
        for s in VERB_SUF:
            if f.endswith(s) and len(f) - len(s) >= 4:
                return f[:-len(s)]
    for s in NOUN_SUF:
        if f.endswith(s) and len(f) - len(s) >= 4:
            if s[0] in 'syn' and f[-len(s) - 1] not in _V:
                continue
            return f[:-len(s)]
    return f


_V = set('aeiou')


def stem_alts(st):
    """Prefixes a stem may surface as: vowel drop (nehr -> nehir), final softening (yukseklig -> yukseklik)."""
    alts = [st]
    if len(st) >= 4 and st[-1] not in _V and st[-2] not in _V and not st.isdigit():
        alts.append(st[:-1] + ('u' if st[-3] in 'ou' else 'i') + st[-1])
    soft = {'g': 'k', 'd': 't', 'b': 'p', 'c': 'c'}
    if len(st) >= 4 and st[-1] in soft and st[-1] != soft[st[-1]]:
        alts.append(st[:-1] + soft[st[-1]])
    return alts


def tok_match(tok, st, exact):
    if exact:
        return tok == st
    return any(tok.startswith(a) for a in stem_alts(st))


class Term:
    __slots__ = ('surf', 'f', 'cap', 'gen', 'pos', 'weak', 'st', 'exact', 'verb')

    def __init__(self, surf, f, cap, gen, pos, verb=False):
        self.surf, self.f, self.cap, self.gen, self.pos, self.verb = surf, f, cap, gen, pos, verb
        self.weak = f in WEAK
        self.exact = len(f) <= 3 and not f.isdigit()
        self.st = stem(f, proper=False, verb=verb) if not cap else f

    def hit(self, tokens):
        return any(tok_match(t, self.st, self.exact) for t in tokens)

    def fts(self):
        """OR-group of prefixes for the index ([prefix, is_prefix])."""
        if self.exact:
            return [(self.f, False)]
        return [(a, True) for a in stem_alts(self.st)]


def parse_words(q):
    """Question words with apostrophe suffixes cut off: [(surface, folded, capitalised, genitive, position)]."""
    out = []
    raw = re.findall(r"[^\s,.;:!?()\"“”]+", q.strip())
    for i, r in enumerate(raw):
        parts = QUOTE.split(r)
        w = parts[0]
        f = re.sub(r'[^0-9a-z.]', '', fold(w)).strip('.')
        if not f:
            continue
        suf = fold(parts[1]) if len(parts) > 1 else ''
        gen = suf in ('nin', 'nun', 'in', 'un', 'n') or suf.endswith(('nin', 'nun')) and len(suf) <= 4
        if not suf and f in ('dunyanin', 'turkiyenin'):
            f, gen = f[:-3], True
        rawf = re.sub(r"[^0-9a-z.']", '', fold(QUOTE.sub("'", r))).strip(".'")
        out.append((w, f, w[:1].isupper(), gen, i, rawf))
    return out


class Q:
    def __init__(self, q):
        self.q = q
        self.qf = fold(q)
        self.words = parse_words(q)
        qf = ' ' + ' '.join(re.sub(r'[^0-9a-z]', ' ', self.qf).split()) + ' '
        self.want_def = bool(re.search(r' (nedir|kimdir|kimdi|ne demek|ne demektir|nelerdir|hakkinda|anlami) ', qf))
        self.want_when = bool(re.search(r' (ne zaman|hangi (yil|tarih|yuzyil)|kac yilinda|kacinda|tarihi ne) ', qf))
        self.want_where = bool(re.search(r' (nerede|nerededir|neresinde|hangi (bolge|il|ulke|sehir|kita|sehir)[a-z]*) ', qf))
        self.want_num = bool(re.search(r' (kac|ne kadar)', qf)) or self.want_when
        self.want_who = bool(re.search(r' kim ', qf)) and not self.want_def
        ws = [w for w in self.words if w[1] not in STOP and len(w[1]) >= 2]
        last_pos = ws[-1][4] if ws else -1
        self.terms = []
        for w in ws:
            is_verb = (w[4] == last_pos and not w[2] and len(ws) > 1 and not w[3]
                       and bool(re.search(r'(d|t)(i|u)$|m(i|u)s$|(a|e)r$', w[1]))
                       and not any(w[1].startswith(m) for m in MEASURE))
            self.terms.append(Term(w[0], w[1], w[2] and w[4] > 0 or w[2] and w[3], w[3], w[4], verb=is_verb))
        self.req = [t for t in self.terms if not t.weak] or list(self.terms)
        self.sup = [stem(fold(m.group(1))) for m in re.finditer(r"\ben\s+([a-zçğıöşü]{3,})", q, re.I)
                    if fold(m.group(1)) not in STOP]
        self.rel = self._relation()
        if not self.terms:
            self.want_def = False
        if not self.want_def and len(self.req) == 1 and not (self.want_when or self.want_where or self.want_num or self.want_who) \
                and not self.rel and len(self.words) <= 3:
            self.want_def = True  # "Fotosentez" / "fotosentez nedir"

    def _relation(self):
        w = self.words
        if len(w) < 3 or w[-1][1] not in WH_END:
            return None
        for i in range(len(w) - 2, -1, -1):
            if w[i][3]:
                R = [x for x in w[i + 1:-1]]
                if not 1 <= len(R) <= 4:
                    return None
                j = i
                X = [w[i]]
                while j - 1 >= 0 and w[j - 1][2] and w[j - 1][4] == w[j][4] - 1 and w[j - 1][4] > 0 or \
                        (j - 1 == 0 and w[0][2] and w[j][4] == 1):
                    j -= 1
                    X.insert(0, w[j])
                    if len(X) >= 3:
                        break
                rt = [fold(x[1]) for x in R]
                head = stem(rt[-1])
                if any(head.startswith(m) for m in MEASURE) or rt[-1] in STOP:
                    return None
                return {'X': [x[1] for x in X], 'Xsurf': ' '.join(x[0] for x in X), 'R': rt}
        return None


# ------------------------------------------------------------------ sentences
WIKILINK = re.compile(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]')


def split_sentences(text):
    text = WIKILINK.sub(r'\1', text)   # "[[hedef|metin]]" left in a few dump passages -> "metin"
    out = []
    for part in SENT_SPLIT.split(text):
        if out and re.search(r'(\b\w{1,2}|\b[IVXLC]+|\b(Dr|Prof|Doç|vb|vs|bkz|yy|St|Av|Op|Yrd))\.$', out[-1]):
            out[-1] += ' ' + part
        else:
            out.append(part)
    return [s.strip() for s in out if len(s.strip()) > 15 and not JUNK.search(s)]


def clean(s):
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r'\(\s*[;,]?\s*\)', '', s)
        s = re.sub(r'\(\s*;\s*', '(', s)
    s = re.sub(r'\s+([,.;])', r'\1', s)
    return ' '.join(s.split())


def strip_paren(s):
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r'\([^()]*\)', ' ', s)
    return ' '.join(s.split())


def base_title(t):
    return strip_paren(t).strip()


def words_with_case(s):
    """[(original token, folded token, start, end)] — same segmentation as toks()."""
    return [(m.group(), fold(m.group()), m.start(), m.end()) for m in TOK.finditer(s)]


def lenient_eq(a, b):
    if a == b:
        return True
    if len(a) >= 4 and len(a) == len(b) and a[:-1] == b[:-1] and {a[-1], b[-1]} in ({'d', 't'}, {'b', 'p'}, {'c', 'g'}):
        return True
    return False


def lenient_group(x):
    g = [(x, False)]
    sw = {'d': 't', 't': 'd', 'b': 'p', 'p': 'b'}
    if len(x) >= 4 and x[-1] in sw:
        g.append((x[:-1] + sw[x[-1]], False))
    return g


def find_seq(tokens, seq, start=0):
    n = len(seq)
    for i in range(start, len(tokens) - n + 1):
        if all(lenient_eq(tokens[i + k], seq[k]) for k in range(n)):
            return i
    return -1


# ------------------------------------------------------------------ the QA engine
class Answer(dict):
    pass


class QA:
    """ix must provide:
      titles(tfold)            -> [(title, alen, disamb)] exact folded-title matches
      titles_prefix(prefix,n)  -> [(title, tfold, alen, disamb)] folded titles starting with prefix
      lead(title)              -> {'title','url','body','alen'} first passage of the article (or None)
      passages(title, n)       -> [doc] passages of the article in order (offline: only the lead)
      search(groups, n, lead_only, order='bm25'|'alen') -> [doc]; groups = AND of OR-groups [(text, is_prefix)]
    """

    def __init__(self, ix):
        self.ix = ix

    # ---------- entity resolution
    def _pick(self, rows, q):
        """rows: [(title, alen, disamb)] candidates for one span; prefers parenthetical words found in the question."""
        good = [r for r in rows if not r[2] and 'listesi' not in fold(r[0])]
        if not good:
            return None
        def key(r):
            par = re.findall(r'\((.*?)\)', r[0])
            in_q = par and all(any(tf in q.qf for tf in re.findall(r'[0-9a-z]{3,}', fold(p))) for p in par)
            return (1 if in_q else 0, 1 if not par else 0, r[1])
        return max(good, key=key)[0]

    def _exact(self, q, span):
        """Article for one span of question words: exact folded title, 'title (…)', suffix variant; None if only a
        disambiguation page matches ('disamb' returned instead)."""
        keys = [' '.join(w[1] for w in span)]
        if any("'" in w[5] for w in span[:-1]):
            keys = [' '.join(w[5] for w in span[:-1]) + ' ' + span[-1][1]]   # only "İstanbul'un Fethi" itself
        elif any(w[3] for w in span):
            keys.append(' '.join(w[5] for w in span))
        if span[0][1] in ORD_WORDS:
            keys.append(' '.join([ORD_WORDS[span[0][1]]] + [w[1] for w in span[1:]]))
        last = span[-1]
        if not last[3] and stem(last[1]) != last[1] and len(span) == 1 and span[0][4] == 0 or not last[2] and not last[3]:
            vs = [stem(last[1]), last[1][:-1] if last[1][-1] in _V and len(last[1]) >= 5 else None]
            for v in [x for i, x in enumerate(vs) if x and x != last[1] and x not in vs[:i]]:
                keys.append(' '.join([w[1] for w in span[:-1]] + [v]))   # "Telefonu" -> telefon
        disamb = False
        for key in keys:
            rows = [(t, a, d) for t, a, d in self.ix.titles(key)]
            par = [(t, a, d) for t, tf, a, d in self.ix.titles_prefix(key + ' (', 20)]
            exact_ok = [r for r in rows if not r[2]]
            if exact_ok:
                t = self._pick(exact_ok + [r for r in par if self._par_in_q(r[0], q)], q)
                if t:
                    return t
            if rows and not exact_ok:
                disamb = True
                t = self._pick([r for r in par if self._par_in_q(r[0], q)], q)
                if t:
                    return t
                continue
            t = self._pick([r for r in par if self._par_in_q(r[0], q)], q)
            if t:
                return t
            rows2 = [(tt, a, d) for tt, tf, a, d in self.ix.titles_prefix(key, 20)
                     if re.fullmatch(r'[a-z]{1,3}', tf[len(key):] or '-')]
            t = self._pick(rows2, q)
            if t:
                return t
        return 'disamb' if disamb else None

    def _par_in_q(self, title, q):
        par = re.findall(r'\((.*?)\)', title)
        return bool(par) and all(any(tf in q.qf for tf in re.findall(r'[0-9a-z]{3,}', fold(p))) for p in par)

    def _alias(self, q, span):
        """Article whose lead names this span ("Fatih Sultan Mehmet" -> II. Mehmed, "Atatürk" -> Mustafa Kemal Atatürk)."""
        seq = [w[1] for w in span]
        if len(seq) == 1 and len(seq[0]) < 4:
            return None
        cands = []
        for d in self.ix.search([lenient_group(x) for x in seq], 40, True, 'alen'):
            if d.get('alen', 0) < 5000 or d.get('disamb'):
                continue
            tt = toks(d['title'])
            i = find_seq(tt, seq)
            if i >= 0 and i + len(seq) < len(tt):
                continue  # "Fatih Sultan Mehmet Köprüsü": something named after it
            if len(seq) == 1:
                if not (tt and lenient_eq(tt[-1], seq[0]) and len(tt) > 1 and '(' not in d['title']):
                    continue
                if not all(w[:1].isupper() or w[:1].isdigit() for w in TOK.findall(d['title'])):
                    continue  # "Cep telefonu" is not a name for "Telefon"
            else:
                if i < 0:
                    if not any(lenient_eq(a, b) for a in tt for b in seq):
                        continue
                    if not any(find_seq(toks(x), seq) >= 0 for x in split_sentences(d['body'])[:2]):
                        continue
            cands.append(d)
        if cands:
            return max(cands, key=lambda d: d.get('alen', 0))['title']
        return None

    def _disamb_ext(self, q, span):
        key = ' '.join(w[1] for w in span)
        ext = [(tt, a) for tt, tf, a, d in self.ix.titles_prefix(key + ' ', 40) if not d and '(' not in tt]
        ext.sort(key=lambda r: -r[1])
        if ext and ext[0][1] >= 8000 and (len(ext) == 1 or ext[0][1] >= 2 * ext[1][1]):
            return ext[0][0]
        return None

    def resolve(self, q):
        words = [w for w in q.words if (w[1] not in STOP or w[1] in ORD_WORDS or w[1] in CONNECT) and w[1] not in WH_END]
        spans = []
        for n in range(min(5, len(words)), 0, -1):
            for i in range(0, len(words) - n + 1):
                span = words[i:i + n]
                if any(span[k + 1][4] != span[k][4] + 1 for k in range(n - 1)):
                    continue
                if all(w[1] in WEAK for w in span) or span[-1][1] in STOP or span[0][1] in CONNECT:
                    continue
                if n == 1 and (not (span[0][2] or q.want_def) or len(span[0][1]) < 2):
                    continue
                spans.append(span)
        caps = self._cap_spans(q)
        longest = caps[0] if caps else None
        found, alias_done, disambs = [], False, []
        for span in spans:
            if longest and not alias_done and len(span) < len(longest) and len(longest) >= 2:
                alias_done = True
                t = self._alias(q, longest)
                if t:
                    found.append((t, longest))
                    if not q.want_def:
                        break
            t = self._exact(q, span)
            if t == 'disamb':
                disambs.append(span)
                continue
            if t:
                found.append((t, span))
                if not q.want_def:
                    break
        if not found:
            for span in caps:
                if len(span) == 1:
                    t = self._alias(q, span)
                    if t:
                        found.append((t, span))
                        break
        if not found:
            for span in disambs:
                t = self._disamb_ext(q, span)
                if t:
                    found.append((t, span))
                    break
        if not found:
            return None
        if longest and len(longest) >= 2:
            lp = {w[4] for w in longest}
            found = [f for f in found if lp <= {w[4] for w in f[1]} or f[1] is longest]
            if not found:
                return None
        if q.want_def and len(found) > 1:
            # "Python programlama dili nedir": the article whose first sentence covers the rest of the question
            def cover(f):
                lead = self.ix.lead(f[0])
                sl = split_sentences(lead['body']) if lead else []
                tk = toks(sl[0]) if sl else []
                pos = {w[4] for w in f[1]}
                return (sum(1 for t in q.terms if t.pos not in pos and t.hit(tk)), len(f[1]))
            found.sort(key=lambda f: (all(w[2] for w in f[1]), len(f[1]), cover(f)), reverse=True)
        t, span = found[0]
        return {'title': t, 'span': [w[4] for w in span]}

    def _cap_spans(self, q):
        ws = [w for w in q.words if w[1] not in STOP]
        spans, cur = [], []
        for w in ws:
            if w[2] and (not cur or w[4] == cur[-1][4] + 1 and not cur[-1][3] and '\'' not in cur[-1][5]):
                cur.append(w)
            else:
                if cur:
                    spans.append(cur)
                cur = [w] if w[2] else []
        if cur:
            spans.append(cur)
        return sorted(spans, key=lambda s: -len(s))

    # ---------- relation votes
    def relation(self, q):
        rel = q.rel
        X, R = rel['X'], rel['R']
        rterms = [Term(r, r, False, False, 0) for r in R]
        head = rterms[-1]
        groups = [[(x, True)] for x in X] + [head.fts()]
        votes, evidence = {}, {}

        def vote(key, w, d, sent, ans):
            votes[key] = votes.get(key, 0) + w
            evidence.setdefault(key, []).append((w, d, sent, ans))

        xt = self._title_for(X)
        seen = set()
        for d in self.ix.search(groups, 300, True, 'alen') + self.ix.search(groups, 150, True):
            if d['id'] in seen:
                continue
            seen.add(d['id'])
            title = d['title']
            if title == xt or 'listesi' in fold(title) or d.get('disamb'):
                continue
            bt = base_title(title)
            btt = toks(bt)
            for si, sent in enumerate(split_sentences(d['body'])[:3]):
                for kind, ans in self._rel_sentence(sent, X, rterms, btt, bt):
                    if kind == 'subject':
                        vote(fold(ans), 3 if si == 0 else 2, d, sent, ans)
                    else:
                        vote(fold(ans), 1, d, sent, ans)
        # X's own article: "Kanada'nın başkenti Ottawa;" / "Başkenti Ankara'dır."
        if xt:
            for p in self.ix.passages(xt, 40):
                for sent in split_sentences(p['body']):
                    for kind, ans in self._rel_sentence(sent, X, rterms, None, None, own=True):
                        vote(fold(ans), 2, p, sent, ans)
        if not votes:
            return None
        ranked = sorted(votes.items(), key=lambda kv: -kv[1])
        top, sc = ranked[0]
        second = ranked[1][1] if len(ranked) > 1 else 0
        if sc < 2 or second > 0 and sc < 2 * second + 1:
            return None
        ev = sorted(evidence[top], key=lambda e: -e[0])[0]
        return {'answer': ev[3], 'doc': ev[1], 'sentence': ev[2]}

    def _rel_sentence(self, sent, X, rterms, btt, bt, own=False):
        """Yields ('subject', title) for "T…, X'in R(dir)" and ('name', Z) for "X'in R Z"."""
        plain = strip_paren(sent)
        wc = words_with_case(plain)
        tk = [w[1] for w in wc]
        caps = [w[0][:1].isupper() for w in wc]
        out = []
        starts = []
        for xi in self._x_positions(tk, X):
            xe = xi + len(X)
            glued = tk[xe - 1] != X[-1] and not lenient_eq(tk[xe - 1], X[-1])
            k = xe if glued else (xe + 1 if xe < len(tk) and tk[xe] in GEN else xe)
            if k == xe and not glued and len(rterms) < 2:
                continue
            if any(t in BLOCK_BEFORE_X for t in tk[max(0, xi - 3):xi]):
                continue
            starts.append((k, self._comma_after(plain, wc, k - 1)))
        if own:
            if tk and tok_match(tk[0], rterms[0].st, rterms[0].exact):
                starts.append((0, False))                    # "Başkenti Ankara'dır."
            for i, t in enumerate(tk[:-1]):
                if t in ('ulkenin', 'ulkesinin', 'sehrin', 'kentin', 'ilin', 'devletin'):
                    starts.append((i + 1, False))
        for k, comma in starts:
            m = self._match_r(tk, k, rterms, comma, caps)
            if m is None:
                continue
            hend, rem = m
            if rem not in ('', 'i', 'si', 'u', 'su', 'dir', 'idir', 'sidir', 'tir', 'dur', 'udur', 'sudur', 'tur', 'ir', 'ur'):
                continue
            z = self._proper_after(plain, wc, hend) if rem in ('', 'i', 'si', 'u', 'su') else None
            if z:
                if fold(z).split()[0] in X or tk[hend + 1] in GEN:
                    continue
                if hend + 1 + len(z.split()) < len(tk) and tk[hend + len(z.split()) + 1] in GEN:
                    continue  # "başkenti Ankara'nın ..." -> not an answer
                out.append(('name', z))
            elif not own and btt and tk[:len(btt)] == btt and not any(lenient_eq(a, b) for a in btt for b in X):
                if hend + 1 < len(wc) and plain[wc[hend][3]:wc[hend + 1][2]].strip() == ',' and caps[hend + 1]:
                    continue  # "T, X'in başkenti, Ottava'da …": an appositive about another place
                out.append(('subject', bt))
        return out

    def _title_for(self, X):
        rows = self.ix.titles(' '.join(X))
        return self._pick(rows, Q(' '.join(X))) if rows else None

    def _x_positions(self, tk, X):
        out = []
        n = len(X)
        for i in range(len(tk) - n + 1):
            ok = all(lenient_eq(tk[i + j], X[j]) for j in range(n - 1))
            last = tk[i + n - 1]
            if ok and (lenient_eq(last, X[-1]) or last in (X[-1] + 'nin', X[-1] + 'nun', X[-1] + 'in', X[-1] + 'un')):
                out.append(i)
        return out

    def _comma_after(self, plain, wc, idx):
        """is the token at idx directly followed by a comma in the plain sentence?"""
        if 0 <= idx < len(wc):
            return plain[wc[idx][3]:wc[idx][3] + 1] == ','
        return False

    def _match_r(self, tk, k, rterms, comma_ok, caps):
        """R words in order within 6 tokens after the possessor; returns (index of head token, suffix after stem)."""
        j, i = 0, k
        limit = k + 6 + len(rterms)
        last_hit = None
        while i < len(tk) and i < limit and j < len(rterms):
            t = tk[i]
            if rterms[j].exact and t == rterms[j].f or not rterms[j].exact and tok_match(t, rterms[j].st, False):
                if j == len(rterms) - 1:
                    prev = tk[i - 1] if i - 1 >= 0 else ''
                    if prev in BLOCK_MOD or ORDINAL.match(prev):
                        return None
                last_hit = i
                j += 1
            else:
                if (t in GEN or re.search(r'[aeiou](nin|nun)$|[^aeiou](in|un)in$', t) and len(t) >= 5) and not comma_ok:
                    return None  # another possessor in between
                if ORDINAL.match(t) or t in BLOCK_MOD:
                    return None
                if caps[i] and not comma_ok:
                    return None  # another named place in between ("Brezilya'nın … Pernambuco Eyaleti başkenti")
            i += 1
        if j < len(rterms):
            return None
        head = rterms[-1]
        t = tk[last_hit]
        alt = next(a for a in stem_alts(head.st) if t.startswith(a)) if not head.exact else t
        return last_hit, t[len(alt):]

    def _proper_after(self, plain, wc, hend):
        """Capitalised name right after the relation word: 'başkenti Ankara'da' -> 'Ankara'.
        Only plain spaces may separate the words ("başkenti, Arap…" and "Delhi'de" end the name)."""
        out = []
        for i in range(hend + 1, min(len(wc), hend + 5)):
            o, f, st, _ = wc[i]
            if plain[wc[i - 1][3]:st] != ' ':
                break
            if o[:1].isupper() and f not in MONTHS:
                out.append(o)
            elif out and f in ('de', 'da') and len(out) < 3:
                out.append(o)
            else:
                break
        while out and fold(out[-1]) in ('de', 'da'):
            out.pop()
        return ' '.join(out) if out else None

    # ---------- entity sentences
    def entity_answer(self, q, ent):
        title = ent['title']
        lead = self.ix.lead(title)
        if not lead:
            return None
        span = set(ent['span'])
        rem = [t for t in q.terms if t.pos not in span and (not t.weak or any(t.f.startswith(m) for m in MEASURE))]
        weak = [t for t in q.terms if t.pos not in span and t.weak]
        ent_toks = [t for t in toks(base_title(title)) if len(t) >= 4] + \
                   [w[1] for w in q.words if w[4] in span and len(w[1]) >= 4]
        if q.want_def and not rem:
            sl = split_sentences(lead['body'])
            if not sl:
                return None
            out = sl[0]
            if len(out) < 70 and len(sl) > 1:
                out += ' ' + sl[1]
            return {'doc': lead, 'sentence': out}
        agent_t = q.terms[-1] if q.want_who and q.terms and q.terms[-1].verb and q.terms[-1].pos not in span else None
        agent = agent_t is not None
        rem = [t for t in rem if t is not agent_t]
        qspan = [w[1] for w in q.words if w[4] in span]
        full_seqs = [qspan] if len(qspan) >= 2 else [toks(base_title(title)), qspan]
        event = any(t.verb for t in rem) or q.want_when
        best = None
        for p in self.ix.passages(title, 40):
            for si, s in enumerate(split_sentences(p['body'])):
                tk = toks(s)
                if not all(t.hit(tk) for t in rem):
                    continue
                lead_pos = p.get('ord', 0) == 0 and si < 3
                mentions = any(find_seq(tk, fs) >= 0 or len(fs) == 1 and any(tok_match(t, fs[0], False) for t in tk)
                               for fs in full_seqs if fs)
                if not (lead_pos or mentions):
                    continue
                if event and not (mentions or p.get('ord', 0) == 0 and si == 0):
                    continue
                sf = ' '.join(tk)
                if q.want_when and not (re.search(r'\b1\d{3}\b|\b20\d{2}\b', sf) or any(m in tk for m in MONTHS)):
                    continue
                if q.want_num and not re.search(r'\d', s):
                    continue
                if q.want_where and not WHERE_CUE.search(sf):
                    continue
                if q.sup and not self._sup_ok(tk, q):
                    continue
                if agent:
                    names = [w[0] for w in words_with_case(strip_paren(s))[1:] if w[0][:1].isupper() and w[1] not in ent_toks]
                    vst = stem(agent_t.f, verb=True)
                    vst = vst if len(vst) >= 4 else agent_t.f[:3]
                    if not names or not ('tarafindan' in tk or any(t.startswith(vst) for t in tk)):
                        continue
                sc = (sum(1 for t in weak if t.hit(tk)) + (2 if lead_pos else 0) + (1 if mentions else 0)
                      - 0.05 * si - 0.3 * p.get('ord', 0))
                if best is None or sc > best[0]:
                    best = (sc, p, s)
        if best:
            return {'doc': best[1], 'sentence': best[2]}
        return None

    def _sup_ok(self, tk, q):
        s = ' '.join(tk)
        for a in q.sup:
            if not re.search(r'\ben ' + re.escape(a), s):
                return False
        if re.search(r'\ben [a-z]+ (\d+|[a-z]*(inci|unci|nci|ncu)\b)', s) or re.search(r'(inci|unci|nci|ncu|\d) en ', s):
            return False
        return True

    # ---------- main
    def answer(self, question):
        q = Q(question)
        if not q.terms:
            return {'confident': False, 'q': q}
        if q.rel and not TEMPORAL_Q.search(q.qf):
            r = self.relation(q)
            if r:
                return {'confident': True, 'kind': 'relation', 'answer': r['answer'], 'doc': r['doc'],
                        'sentence': clean(r['sentence']), 'q': q}
        ent = self.resolve(q)
        if ent:
            r = self.entity_answer(q, ent) if not q.rel else None
            if r:
                return {'confident': True, 'kind': 'entity', 'doc': r['doc'], 'sentence': clean(r['sentence']), 'q': q,
                        'entity': ent['title']}
            lead = self.ix.lead(ent['title'])
            sl = split_sentences(lead['body']) if lead else []
            return {'confident': False, 'q': q, 'entity': ent['title'], 'doc': lead,
                    'sentence': clean(sl[0]) if sl else ''}
        return {'confident': False, 'q': q}


def render(res):
    """Answer text (markdown) for a confident result; the sentence is quoted verbatim."""
    s = res['sentence']
    if res.get('kind') == 'relation':
        return f"**{res['answer']}** — {s}"
    return s
