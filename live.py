"""Live knowledge for Alper AI (v4.2): Turkish Wikipedia API + general web snippets. No AI/model APIs.

lookup(question) -> dict(text, sources, title) or None
  1. topic extraction: strip question words ("nedir", "anlat", "ne işe yarar", "takviyesi"...)
  2. synonym / typo fix: SYN table (bca -> BCAA -> "Dallanmış zincirli aminoasit", creatine -> Kreatin) + difflib fuzzy
  3. tr.wikipedia.org: exact title (redirects) -> else search; a hit is accepted only if its title/lead really
     contains the topic (no random article), answer = first lead sentences copied verbatim, with the URL
  4. otherwise general web search snippets (Bing HTML), quoted verbatim with their URLs
"""
import difflib, html, json, re, threading, time, urllib.parse, urllib.request
from textnorm import fold

UA = 'AlperAI/4.2 (https://yusufalper.com.tr/alper-ai; yusuf571tr@gmail.com)'
WIKI = 'https://tr.wikipedia.org/w/api.php'
TIMEOUT = 6

# folded key -> Wikipedia title (Turkish). Common English names, abbreviations and typos people write.
SYN = {
    'bca': 'Dallanmış zincirli aminoasit', 'bcaa': 'Dallanmış zincirli aminoasit', 'bcaa lar': 'Dallanmış zincirli aminoasit',
    'dallanmis zincirli amino asit': 'Dallanmış zincirli aminoasit', 'dalli zincirli amino asit': 'Dallanmış zincirli aminoasit',
    'branched chain amino acid': 'Dallanmış zincirli aminoasit',
    'creatine': 'Kreatin', 'creatin': 'Kreatin', 'kreatin': 'Kreatin', 'kreatine': 'Kreatin', 'keratin takviyesi': 'Kreatin',
    'kreatin monohidrat': 'Kreatin', 'creatine monohydrate': 'Kreatin',
    'whey': 'Peynir altı suyu proteini', 'whey protein': 'Peynir altı suyu proteini', 'whey proteini': 'Peynir altı suyu proteini',
    'protein tozu': 'Protein tozu', 'protein powder': 'Protein tozu',
    'glutamine': 'Glutamin', 'glutamin': 'Glutamin', 'l glutamin': 'Glutamin',
    'arginine': 'Arginin', 'l arjinin': 'Arginin', 'arjinin': 'Arginin',
    'l carnitine': 'Karnitin', 'l karnitin': 'Karnitin', 'carnitine': 'Karnitin', 'karnitin': 'Karnitin',
    'caffeine': 'Kafein', 'kafein': 'Kafein', 'beta alanine': 'Beta-alanin', 'beta alanin': 'Beta-alanin',
    'omega 3': 'Omega-3 yağ asitleri', 'omega3': 'Omega-3 yağ asitleri', 'balik yagi': 'Balık yağı', 'fish oil': 'Balık yağı',
    'vitamin d': 'D vitamini', 'd vitamini': 'D vitamini', 'vitamin c': 'C vitamini', 'c vitamini': 'C vitamini',
    'vitamin b12': 'B12 vitamini', 'b12': 'B12 vitamini', 'b12 vitamini': 'B12 vitamini', 'vitamin a': 'A vitamini',
    'vitamin e': 'E vitamini', 'vitamin k': 'K vitamini',
    'magnesium': 'Magnezyum', 'zinc': 'Çinko', 'cinko': 'Çinko', 'iron': 'Demir', 'calcium': 'Kalsiyum',
    'melatonin': 'Melatonin', 'collagen': 'Kolajen', 'kolajen': 'Kolajen', 'kollajen': 'Kolajen',
    'ashwagandha': 'Withania somnifera', 'zma': 'ZMA', 'pre workout': 'Antrenman öncesi takviye',
    'protein': 'Protein', 'karbonhidrat': 'Karbonhidrat', 'carbohydrate': 'Karbonhidrat', 'kalori': 'Kalori',
    'insulin': 'İnsülin', 'insülin': 'İnsülin', 'kolesterol': 'Kolesterol', 'cholesterol': 'Kolesterol',
    'diabetes': 'Diyabet', 'seker hastaligi': 'Diyabet', 'diyabet': 'Diyabet', 'tansiyon': 'Hipertansiyon',
    'yuksek tansiyon': 'Hipertansiyon', 'hypertension': 'Hipertansiyon', 'covid': 'COVID-19', 'korona': 'COVID-19',
    'koronavirus': 'COVID-19', 'dna': 'DNA', 'rna': 'RNA', 'atp': 'Adenozin trifosfat', 'bmi': 'Vücut kitle indeksi',
    'vki': 'Vücut kitle indeksi', 'vucut kitle indeksi': 'Vücut kitle indeksi',
    'yapay zeka': 'Yapay zekâ', 'artificial intelligence': 'Yapay zekâ', 'ai': 'Yapay zekâ', 'blockchain': 'Blok zinciri',
    'blok zinciri': 'Blok zinciri', 'bitcoin': 'Bitcoin', 'internet': 'İnternet', 'fotosentez': 'Fotosentez',
    'photosynthesis': 'Fotosentez', 'kara delik': 'Kara delik', 'black hole': 'Kara delik', 'gravity': 'Kütleçekim',
    'yercekimi': 'Kütleçekim', 'kutlecekim': 'Kütleçekim', 'big bang': 'Büyük Patlama', 'buyuk patlama': 'Büyük Patlama',
    'ataturk': 'Mustafa Kemal Atatürk', 'mustafa kemal': 'Mustafa Kemal Atatürk',
}
SUPPLEMENT_WORDS = ('suplement', 'supplement', 'takviye', 'destek', 'tozu')
HEALTH = re.compile(r'(takviye|suplement|supplement|vitamin|mineral|ilac|hastalik|tedavi|doz|kreatin|bcaa|protein|kafein|'
                    r'saglik|diyabet|tansiyon|kolesterol|insulin|melatonin|omega|aminoasit|amino asit|beslenme|diyet|kilo)')
HEALTH_NOTE = '\n\n_Bu genel bilgidir, tıbbi tavsiye değildir; takviye ya da ilaç kullanmadan önce doktoruna veya diyetisyenine danış._'

LEAD = re.compile(r"^\s*(peki|acaba|bana|bize|lutfen|hocam|abi|kanka|alper|alper ai)\b[\s,]*")
TAIL = re.compile(r"(?:^|[\s,]+)(nedir|ne demek(tir)?|ne demektir|ne ise yarar|ne ise yariyor|ne icin kullanilir|neye yarar|"
                  r"faydalari (nelerdir|ne)|faydasi ne|zararlari (nelerdir|ne)|nelerdir|kimdir|kim|ne|nasil bir sey|"
                  r"hakkinda( bilgi( ver(ir misin)?)?)?|anlat(ir misin|abilir misin|sana)?|acikla(r misin)?|"
                  r"bilgi ver(ir misin)?|nedir acaba|tanimi|tanimla|kisaca|detayli|biliyor musun|bilir misin|"
                  r"misin|mi|mu)\s*[?.!]*$")


def topic_surface(question):
    """Like topic_of but keeps the original Turkish spelling (for Wikipedia titles): 'Pi sayısı nedir' -> 'pi sayısı'."""
    low = question.replace('İ', 'i').replace('I', 'ı').lower()
    ws = re.findall(r"[0-9a-zçğıöşüâîûéè'’-]+", low)
    fw = [fold(w) for w in ws]
    i, j = 0, len(ws)
    while i < j and LEAD.match(' '.join(fw[i:i + 1]) + ' ') and fw[i] in LEAD_WORDS:
        i += 1
    changed = True
    while changed and j > i:
        changed = False
        for k in range(min(4, j - i), 0, -1):
            tail = ' '.join(fw[j - k:j])
            if TAIL_ONLY.fullmatch(tail):
                j -= k; changed = True; break
    keep = []
    for w, f in zip(ws[i:j], fw[i:j]):
        if any(f.startswith(x) for x in SUPPLEMENT_WORDS):
            continue
        keep.append(re.split(r"['’]", w)[0])
    return ' '.join(keep).strip()


LEAD_WORDS = {'peki', 'acaba', 'bana', 'bize', 'lutfen', 'hocam', 'abi', 'kanka', 'alper', 'ai'}


def topic_of(question):
    """'bca suplementini anlat' -> 'bca' ; 'Creatine nedir?' -> 'creatine'."""
    return fold(topic_surface(question)).replace('-', ' ')


TAIL_ONLY = re.compile(TAIL.pattern.replace('(?:^|[\\s,]+)', '').replace('\\s*[?.!]*$', ''))


def _strip_suffix(t):
    for suf in ('larini', 'lerini', 'sini', 'sunu', 'ini', 'unu', 'yi', 'yu', 'i', 'u', 'nin', 'nun', 'in', 'un'):
        if t.endswith(suf) and len(t) - len(suf) >= 3:
            yield t[:-len(suf)]


def correct(topic):
    """Synonym/typo table first (exact, then without Turkish case suffix, then fuzzy). Returns (title_or_None, topic)."""
    if not topic:
        return None, topic
    if topic in SYN:
        return SYN[topic], topic
    for w in [topic] + list(_strip_suffix(topic)):
        if w in SYN:
            return SYN[w], w
    last = topic.split()[-1]
    for w in list(_strip_suffix(last)):
        k = ' '.join(topic.split()[:-1] + [w])
        if k in SYN:
            return SYN[k], k
    if len(topic) >= 5:
        m = difflib.get_close_matches(topic, SYN.keys(), n=1, cutoff=0.86)
        if m:
            return SYN[m[0]], m[0]
    return None, topic


# ------------------------------------------------------------------ HTTP with a small cache
_cache, _lock = {}, threading.Lock()


def _get(url, ttl=6 * 3600, headers=None):
    now = time.time()
    with _lock:
        hit = _cache.get(url)
        if hit and now - hit[0] < ttl:
            return hit[1]
    req = urllib.request.Request(url, headers={'User-Agent': UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        data = r.read().decode('utf-8', 'replace')
    with _lock:
        if len(_cache) > 2000:
            _cache.clear()
        _cache[url] = (now, data)
    return data


def _wiki(params):
    params = {'format': 'json', 'formatversion': '2', **params}
    return json.loads(_get(WIKI + '?' + urllib.parse.urlencode(params)))


def wiki_page(title):
    d = _wiki({'action': 'query', 'titles': title, 'redirects': '1', 'prop': 'extracts|info|pageprops',
               'exintro': '1', 'explaintext': '1', 'inprop': 'url', 'ppprop': 'disambiguation'})
    pages = d.get('query', {}).get('pages', [])
    if not pages or pages[0].get('missing') or 'invalid' in pages[0]:
        return None
    p = pages[0]
    return {'title': p['title'], 'url': p.get('canonicalurl') or p.get('fullurl'), 'extract': p.get('extract') or '',
            'disambig': 'pageprops' in p and 'disambiguation' in p.get('pageprops', {})}


def wiki_search(q, n=5):
    d = _wiki({'action': 'query', 'list': 'search', 'srsearch': q, 'srlimit': str(n), 'srinfo': 'suggestion', 'srprop': ''})
    qq = d.get('query', {})
    return [r['title'] for r in qq.get('search', [])], qq.get('searchinfo', {}).get('suggestion')


SENT = re.compile(r'(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9"“(])')


def lead_sentences(extract, max_chars=650, max_sents=3):
    text = re.sub(r'\s*\([^()]{0,120}\)', '', extract)  # drop pronunciations / dates in parentheses for readability
    text = re.sub(r'\s+', ' ', text.replace('\n', ' ')).strip()
    out, carry = '', ''
    for s in SENT.split(text):
        s = (carry + ' ' + s.strip()).strip() if carry else s.strip()
        carry = ''
        if not s:
            continue
        if len(s) < 12:
            carry = s
            continue
        if out and (len(out) + len(s) > max_chars or out.count('. ') + 1 >= max_sents):
            break
        out = (out + ' ' + s).strip()
    return out


def _matches(topic, page):
    """Accept a search hit only if it is really about the topic: title ~ topic, or the lead opens with the topic."""
    t = fold(page['title']).replace('-', ' ')
    t = re.sub(r'\s*\(.*?\)', '', t)
    tp = topic.replace('-', ' ')
    if not tp:
        return False
    if t == tp or difflib.SequenceMatcher(None, t, tp).ratio() >= 0.8:
        return True
    lead = fold(page['extract'][:200]).replace('-', ' ')
    stems = [w if len(w) <= 5 else w[:-2] for w in tp.split()]
    if lead.startswith(' '.join(stems)) or all(re.search(r'\b' + re.escape(s), t) for s in stems if len(s) >= 2):
        return True
    return False


def find_wiki(question):
    surf = topic_surface(question)
    topic = topic_of(question)
    title, key = correct(topic)
    cands = []
    if title:
        cands.append((title, True))
    if surf:
        trust = len(surf) >= 3   # an exact title or a Wikipedia redirect is a strong, human-made signal
        cands.append((surf[:1].upper() + surf[1:], trust))
        cands.append((' '.join(w[:1].upper() + w[1:] for w in surf.split()), trust))
    tried = set()
    for t, trusted in cands:
        if t in tried:
            continue
        tried.add(t)
        try:
            p = wiki_page(t)
        except Exception:
            p = None
        if p and p['extract'] and not p['disambig'] and (trusted or _matches(topic, p)):
            return p, topic
    if not topic or len(topic) < 2:
        return None, topic
    try:
        hits, sugg = wiki_search(surf or topic)
        if not hits and sugg:
            hits, _ = wiki_search(sugg)
            topic = fold(sugg)
    except Exception:
        return None, topic
    for h in hits[:3]:
        try:
            p = wiki_page(h)
        except Exception:
            continue
        if p and p['extract'] and not p['disambig'] and _matches(topic, p):
            return p, topic
    return None, topic


# ------------------------------------------------------------------ general web (search-engine snippets, quoted)
def web_snippets(question, n=3):
    url = 'https://www.bing.com/search?' + urllib.parse.urlencode({'q': question, 'setlang': 'tr', 'cc': 'TR'})
    try:
        page = _get(url, ttl=3600, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                                                          '(KHTML, like Gecko) Chrome/124 Safari/537.36',
                                            'Accept-Language': 'tr-TR,tr;q=0.9'})
    except Exception:
        return []
    out = []
    for block in re.findall(r'<li class="b_algo.*?</li>', page, flags=re.S):
        m = re.search(r'<h2[^>]*>\s*<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>', block, flags=re.S)
        s = re.search(r'<p[^>]*>(.*?)</p>', block, flags=re.S)
        if not m or not s:
            continue
        clean = lambda x: html.unescape(re.sub(r'<[^>]+>', '', x)).replace('\xa0', ' ').strip()
        snip = re.sub(r'^(Web)?\s*\d{1,2} \w{3,8} \d{4}\s*[·—-]\s*', '', clean(s.group(1)))
        link = html.unescape(m.group(1))
        u = re.search(r'[?&]u=a1([^&]+)', link)
        if u:
            import base64
            try:
                link = base64.urlsafe_b64decode(u.group(1) + '=' * (-len(u.group(1)) % 4)).decode()
            except Exception:
                pass
        if len(snip) > 40 and 'bing.com' not in link:
            out.append({'title': clean(m.group(2))[:120], 'url': link, 'snippet': snip, 'origin': 'web'})
        if len(out) >= n:
            break
    return out


def context_sources(question, n=3):
    """Full-text Wikipedia hits + web snippets for questions that are not plain definitions; the caller ranks their
    sentences with the same rules as our index (search.score_external) and only quotes a sentence that covers the question."""
    out = []
    from qa import STOP
    kw = ' '.join(w for w in re.sub(r"[^0-9a-zçğıöşüâîû\s]", ' ', question.lower().replace("'", ' ')).split()
                  if fold(w) not in STOP and len(w) > 1)
    try:
        hits, sugg = wiki_search(kw or question, n)
        if not hits and sugg:
            hits, _ = wiki_search(sugg, n)
        for h in hits[:n]:
            d = _wiki({'action': 'query', 'titles': h, 'redirects': '1', 'prop': 'extracts|info',
                       'explaintext': '1', 'inprop': 'url'})
            for p in d.get('query', {}).get('pages', []):
                if p.get('extract'):
                    out.append({'title': f"Vikipedi: {p['title']}", 'url': p.get('canonicalurl') or p.get('fullurl'),
                                'snippet': re.sub(r'\n+=+[^=\n]+=+\n+', '\n', p['extract'])[:20000], 'origin': 'wikipedia-live'})
    except Exception:
        pass
    out += web_snippets(question)
    return out


def lookup(question):
    """Returns {'text','sources','kind'} for a definition-style question, or None (caller says 'Bundan emin değilim')."""
    p, topic = find_wiki(question)
    note = HEALTH_NOTE if HEALTH.search(fold(question) + ' ' + fold(p['title'] if p else '')) else ''
    if p:
        body = lead_sentences(p['extract'])
        if body:
            name = p['title']
            return {'kind': 'wiki-live', 'title': name,
                    'text': f"**{name}**: {body} [1]{note}",
                    'sources': [{'title': f'Vikipedi: {name}', 'url': p['url'], 'snippet': body[:300], 'origin': 'wikipedia-live'}]}
    return None


if __name__ == '__main__':
    import sys
    for q in sys.argv[1:]:
        print('==', q, '->', topic_of(q), correct(topic_of(q))[0])
        r = lookup(q)
        print(r['text'] if r else None)


# ---- v4.2.3: numbers straight from the article's infobox (nüfus, yükseklik, alan) — fast and exact
FACTS = [
    (re.compile(r'\b(nufus\w*|kac kisi)\b'), ('nüfus_toplam', 'nüfus', 'toplam_nüfus', 'nüfus_şehir', 'nüfus_kent', 'nufus'),
     ('nüfus_yılı', 'nüfus_tarihi'), 'nüfusu', 'kişi'),
    (re.compile(r'\b(kac metre|yuksekligi|yuksekliği|ne kadar yuksek)\b'), ('yükseklik', 'yükseklik_m', 'zirve', 'rakım'), (), 'yüksekliği', 'metre'),
    (re.compile(r'\b(yuzolcumu|yuz olcumu|alani kac)\b'), ('yüzölçümü', 'alan_toplam', 'alan', 'yüz_ölçümü'), (), 'yüzölçümü', 'km²'),
    # v4.3: text facts (no digits needed)
    (re.compile(r'\b(baskent\w*)\b'), ('başkent', 'başkenti', 'baskent'), (), 'başkenti', ''),
]
_TEXT_LABELS = {'başkenti', 'konumu'}
_NUMWORDS = re.compile(r'\s*\b(nufus\w*|kac kisi( var| yasiyor)?|kac metre|yuksekligi|ne kadar yuksek|yuzolcumu|yuz olcumu|alani kac|kac(tir)?|nedir|ne kadar|baskent\w*|neresi(dir)?|nerede(dir)?|hangi ulkede|hangi sehir(dir)?)\b\s*')


def _clean_val(v):
    v = re.sub(r'<ref[^>]*/>|<ref.*?</ref>|<!--.*?-->', '', v, flags=re.S)
    v = re.sub(r'\{\{[^{}]*\}\}', '', v)
    v = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', v)
    return html.unescape(v).replace('\xa0', ' ').strip(" '\t")


def _fmt(v):
    if re.fullmatch(r'\d{4,}', v):
        return f'{int(v):,}'.replace(',', '.')
    return v


def infobox_fact(question):
    fq = fold(question)
    for rx, keys, year_keys, label, unit in FACTS:
        if not rx.search(fq):
            continue
        subject = _NUMWORDS.sub(' ', fq).strip(' ?.!')
        subject = re.sub(r"['’]\w*$", '', subject).strip()
        subject = re.sub(r"(?<=\w)(da|de|ta|te|nin|nın|in|ın|un|nun)$", '', subject).strip() if len(subject) > 4 else subject
        if not subject:
            return None
        p, _ = find_wiki(subject + ' nedir')
        if not p:
            p, _ = find_wiki(question)
        if not p:
            return None
        try:
            d = json.loads(_get(WIKI + '?' + urllib.parse.urlencode({'action': 'parse', 'page': p['title'], 'prop': 'wikitext', 'section': 0,
                                                                   'format': 'json', 'formatversion': 2, 'redirects': 1})))
            w = d['parse']['wikitext']
        except Exception:
            return None
        fields = {}
        for m in re.finditer(r'^\|[ \t]*([^=\n]+?)[ \t]*=[ \t]*(.*)$', w, re.M):
            fields[m.group(1).strip().lower()] = _clean_val(m.group(2))
        numeric = label not in _TEXT_LABELS
        if not numeric:
            fields = {k: re.split(r'\s*(?:\||\{\{|\(|<)', v)[0].strip() for k, v in fields.items()}
        val = next((fields[k] for k in keys if fields.get(k) and (re.search(r'\d', fields[k]) or not numeric) and len(fields[k]) < 120), None)
        if not val:
            return None
        year = next((fields[k] for k in year_keys if fields.get(k)), '')
        val = _fmt(val)
        if unit and unit not in val and not re.search(r'[a-zA-Z²]', val):
            val = f'{val} {unit}'
        text = f"**{p['title']}** {label}: **{val}**" + (f" ({year})" if year else '') + ' [1]'
        return {'kind': 'wiki-live', 'title': p['title'], 'text': text,
                'sources': [{'title': f"Vikipedi: {p['title']}", 'url': p['url'], 'snippet': text, 'origin': 'wikipedia-live'}]}
    return None
