"""v4.4 online answer engine (no AI APIs): finds the sentence that answers a question.

answer(question) -> {'kind','text','sources'} or None
  * currency  : TCMB today.xml (Türkiye Cumhuriyet Merkez Bankası) for "dolar/euro/sterlin kaç TL"
  * weather   : open-meteo.com geocoding + forecast ("yarın İstanbul'da hava nasıl")
  * sentence QA over Turkish Wikipedia: full-text search (one API call returns the plain text of the top pages),
    split into sentences, score by question words + the expected answer type (year for "ne zaman", number for "kaç",
    a name for "kim"), and quote the best sentence verbatim with its source.
"""
import json, re, time, urllib.parse, urllib.request, html
from concurrent.futures import ThreadPoolExecutor
from textnorm import fold

UA = 'AlperAI/4.4 (https://yusufalper.com.tr/alper-ai; yusuf571tr@gmail.com)'
WIKI = 'https://tr.wikipedia.org/w/api.php'
_cache = {}


def _get(url, ttl=3600, timeout=3.5):
    now = time.time()
    hit = _cache.get(url)
    if hit and now - hit[0] < ttl:
        return hit[1]
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read().decode('utf-8', 'replace')
    if len(_cache) > 400:
        _cache.clear()
    _cache[url] = (now, data)
    return data


# ------------------------------------------------------------------ currency (TCMB)
CUR = {'dolar': 'USD', 'usd': 'USD', 'euro': 'EUR', 'avro': 'EUR', 'eur': 'EUR', 'sterlin': 'GBP', 'pound': 'GBP',
       'gbp': 'GBP', 'frank': 'CHF', 'yen': 'JPY', 'ruble': 'RUB', 'riyal': 'SAR', 'manat': 'AZN'}


def currency(q):
    f = fold(q)
    if not re.search(r'\b(kac|kur|fiyat|ne kadar|tl|lira)\b', f):
        return None
    code = next((c for w, c in CUR.items() if re.search(r'\b' + w + r'\b', f)), None)
    if not code:
        return None
    try:
        x = _get('https://www.tcmb.gov.tr/kurlar/today.xml', ttl=1800)
    except Exception:
        return None
    m = re.search(r'<Currency[^>]*CurrencyCode="' + code + r'".*?</Currency>', x, re.S)
    d = re.search(r'Tarih="([^"]+)"', x)
    if not m:
        return None
    blk = m.group(0)
    unit = re.search(r'<Unit>(\d+)</Unit>', blk)
    buy = re.search(r'<ForexBuying>([\d.]+)</ForexBuying>', blk)
    sell = re.search(r'<ForexSelling>([\d.]+)</ForexSelling>', blk)
    name = re.search(r'<Isim>([^<]+)</Isim>', blk)
    if not sell:
        return None
    u = int(unit.group(1)) if unit else 1
    t = (f"**{u} {name.group(1).title() if name else code} = {float(sell.group(1)):.4f} TL** (TCMB döviz satış"
         + (f", alış {float(buy.group(1)):.4f} TL" if buy else '') + (f"; {d.group(1)} tarihli kur" if d else '') + ') [1]')
    return {'kind': 'live', 'text': t, 'sources': [{'title': 'TCMB gösterge niteliğindeki kurlar',
                                                     'url': 'https://www.tcmb.gov.tr/kurlar/today.xml', 'snippet': t, 'origin': 'tcmb'}]}


# ------------------------------------------------------------------ weather (open-meteo, no key)
WMO = {0: 'açık', 1: 'az bulutlu', 2: 'parçalı bulutlu', 3: 'kapalı', 45: 'sisli', 48: 'kırağılı sis', 51: 'hafif çisenti',
       53: 'çisenti', 55: 'yoğun çisenti', 61: 'hafif yağmurlu', 63: 'yağmurlu', 65: 'kuvvetli yağmurlu', 66: 'dondurucu yağmur',
       67: 'kuvvetli dondurucu yağmur', 71: 'hafif karlı', 73: 'karlı', 75: 'yoğun karlı', 77: 'kar taneli', 80: 'sağanak',
       81: 'kuvvetli sağanak', 82: 'şiddetli sağanak', 85: 'kar sağanağı', 86: 'yoğun kar sağanağı', 95: 'gök gürültülü fırtına',
       96: 'dolulu fırtına', 99: 'şiddetli dolulu fırtına'}


def weather(q):
    f = fold(q)
    if not re.search(r'\b(hava|havalar|yagmur|kar yag|sicaklik|derece kac|hava durumu)\b', f):
        return None
    if re.search(r'\b(hava yolu|havayolu|hava kuvvet|hava limani|havaalani)\b', f):
        return None
    day = 1 if re.search(r'\byarin\b', f) else (2 if re.search(r'\b(obur gun|ertesi gun)\b', f) else 0)
    words = re.findall(r"[A-ZÇĞİÖŞÜ][\wçğıöşü]+", q)
    city = None
    for w in words:
        w = re.sub(r"['’].*$", '', w)
        if fold(w) in ('yarin', 'bugun', 'hava', 'nasil'):
            continue
        city = w
        break
    if not city:
        m = re.search(r"\b([a-zçğıöşü]{3,})(?:'?(?:da|de|ta|te|daki|deki))\b", q.lower())
        city = m.group(1) if m and fold(m.group(1)) not in ('yarin', 'bugun', 'hava') else None
    if not city:
        return {'kind': 'unsure', 'text': 'Hangi şehrin hava durumunu istiyorsun? Örneğin "Yarın Ankara\'da hava nasıl" yazabilirsin.', 'sources': []}
    try:
        g = json.loads(_get('https://geocoding-api.open-meteo.com/v1/search?' + urllib.parse.urlencode(
            {'name': city, 'count': 1, 'language': 'tr', 'format': 'json'}), ttl=86400))
        loc = (g.get('results') or [None])[0]
        if not loc:
            return None
        w = json.loads(_get('https://api.open-meteo.com/v1/forecast?' + urllib.parse.urlencode(
            {'latitude': loc['latitude'], 'longitude': loc['longitude'], 'timezone': 'auto', 'forecast_days': 3,
             'daily': 'weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max',
             'current_weather': 'true'}), ttl=1200))
    except Exception:
        return None
    dd = w['daily']
    lbl = ['Bugün', 'Yarın', 'Öbür gün'][day]
    txt = (f"**{loc['name']}** — {lbl} ({dd['time'][day]}): {WMO.get(dd['weathercode'][day], 'değişken')}, "
           f"en düşük **{round(dd['temperature_2m_min'][day])}°C**, en yüksek **{round(dd['temperature_2m_max'][day])}°C**")
    pp = (dd.get('precipitation_probability_max') or [None] * 3)[day]
    if pp is not None:
        txt += f", yağış ihtimali %{pp}"
    if day == 0 and w.get('current_weather'):
        txt += f". Şu an {round(w['current_weather']['temperature'])}°C"
    txt += '. [1]'
    return {'kind': 'live', 'text': txt, 'sources': [{'title': 'Open-Meteo hava tahmini', 'url': 'https://open-meteo.com/',
                                                      'snippet': txt, 'origin': 'open-meteo'}]}


# ------------------------------------------------------------------ sentence QA over Wikipedia
STOP = set(fold(w) for w in '''ne nedir neler nelerdir kim kimdir kimin hangi hangisi hangisidir kac kaç nasil nasıl nerede neresi
neredir ne zaman zaman mi mı mu mü midir dir dır acaba bana soyle söyle soyler anlat bir ve ile de da en ki bu şu o
olan oldu olur olarak icin için gibi daha cok çok var yok mi ilk son kadar yil yıl yili tarih tarihi tarihinde sayisi'''.split())
SENT = re.compile(r'(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9"“(])')


def _qtype(f):
    if re.search(r'\bne zaman\b|\bhangi (yil|tarih|yuzyil)|\bkac yilinda\b|\bkacinci yil', f):
        return 'when'
    if re.search(r'\bkim\b|\bkimdir\b|\bkimin\b|\bkim (tarafindan|icat|kesfet|buldu|yazdi|yapti|gitti|kurdu)', f):
        return 'who'
    if re.search(r'\bkac\b|\bne kadar\b|\bsayisi\b', f):
        return 'num'
    if re.search(r'\bnerede\b|\bneresi\b|\bhangi (sehir|ulke|ilde|kita)', f):
        return 'where'
    if re.search(r'\bhangi\w*\b|\ben (buyuk|kucuk|uzun|kisa|yuksek|derin|kalabalik|eski|genis)\b', f):
        return 'which'
    return 'what'


def _stems(f):
    return [w[:5] for w in re.findall(r'[a-z0-9]+', f) if w not in STOP and len(w) > 1]


def _score(sent, stems, qt, f):
    s = fold(sent)
    words = re.findall(r'[a-z0-9]+', s)
    ws = set(w[:5] for w in words)
    hit = sum(1 for st in stems if st in ws or any(w.startswith(st) for w in words))
    if not stems:
        return 0
    sc = hit / len(stems) * 10
    if qt == 'when' and re.search(r'\b1\d{3}\b|\b20\d{2}\b', sent):
        sc += 4
    elif qt == 'num' and re.search(r'\d', sent):
        sc += 3
    elif qt == 'who' and re.search(r'[A-ZÇĞİÖŞÜ][a-zçğıöşü]+ [A-ZÇĞİÖŞÜ][a-zçğıöşü]+', sent):
        sc += 2
    for sup in ('buyuk', 'kucuk', 'uzun', 'yuksek', 'derin', 'kalabalik', 'ilk'):
        if re.search(r'\ben ' + sup + r'|\bilk\b', f) and sup in s:
            sc += 2
    if len(sent) > 400 or len(sent) < 25:
        sc -= 3
    if re.search(r'^\s*(ayrica|bu|bunun|o|ancak|fakat)\b', s):
        sc -= 1
    return sc


def _search_pages(query, n=4):
    p = {'action': 'query', 'format': 'json', 'formatversion': 2, 'generator': 'search', 'gsrsearch': query,
         'gsrlimit': n, 'prop': 'extracts', 'explaintext': 1, 'exlimit': n, 'exchars': 6000, 'redirects': 1}
    d = json.loads(_get(WIKI + '?' + urllib.parse.urlencode(p), ttl=6 * 3600))
    pages = sorted((d.get('query') or {}).get('pages', []), key=lambda x: x.get('index', 99))
    return [(pg['title'], pg.get('extract') or '') for pg in pages if pg.get('extract')]


def sentence_qa(q):
    f = fold(q)
    qt = _qtype(f)
    stems = _stems(f)
    if not stems:
        return None
    words = [w for w in re.findall(r"[\wçğıöşüÇĞİÖŞÜ']+", q) if fold(w) not in STOP]
    query = ' '.join(re.sub(r"['’]\w*$", '', w) for w in words)
    try:
        pages = _search_pages(query)
    except Exception:
        return None
    best = None
    for rank, (title, text) in enumerate(pages):
        text = re.sub(r'\n+=+[^=]+=+\n+', '\n', text)
        tstem = set(_stems(fold(title)))
        bonus = 2 if tstem & set(stems) else 0
        for para in text.split('\n'):
            for i, s in enumerate(SENT.split(para.strip())):
                if not s:
                    continue
                sc = _score(s, stems, qt, f) + bonus - rank * 0.7 - (0 if i else -0.5)
                if not best or sc > best[0]:
                    best = (sc, s.strip(), title)
    if not best or best[0] < 6.5:
        return None
    sc, s, title = best
    url = 'https://tr.wikipedia.org/wiki/' + urllib.parse.quote(title.replace(' ', '_'))
    text = f"{s} [1]"
    return {'kind': 'wiki-live', 'text': text, 'score': round(sc, 1),
            'sources': [{'title': f'Vikipedi: {title}', 'url': url, 'snippet': s, 'origin': 'wikipedia-live'}]}


def answer_live(q):
    for fn in (currency, weather):
        try:
            r = fn(q)
        except Exception:
            r = None
        if r:
            return r
    return None


def answer(q):
    for fn in (currency, weather):
        try:
            r = fn(q)
        except Exception:
            r = None
        if r:
            return r
    return sentence_qa(q)


if __name__ == '__main__':
    import sys
    for q in sys.argv[1:]:
        t = time.time()
        r = answer(q)
        print(f'[{time.time() - t:.1f}s] {q} -> {r and (r.get("score"), r["text"][:200])}')
