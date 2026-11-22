"""Alper AI answer pipeline (no third-party model).

  smalltalk / identity / date-time / arithmetic -> fixed, correct templates
  factual question                              -> our Wikipedia index (+ live snippets the app sent), answer copied
                                                   verbatim from the source sentence; never invented
  open-ended / creative                         -> our from-scratch model, clearly labelled as experimental
"""
import ast, datetime, operator, random, re
from zoneinfo import ZoneInfo
from textnorm import fold
from search import score_external
from qa import render, Q
import live as livekb

TZ = ZoneInfo('Europe/Istanbul')
UNSURE = 'Bundan emin değilim.'

GREET = re.compile(r'^(merhaba|selam(lar)?|sa|selamun aleykum|hey|hi|hello|gunaydin|iyi aksamlar|iyi geceler|iyi gunler|naber|nasilsin|nasilsiniz)\b')
THANKS = re.compile(r'^(tesekkur(ler| ederim)?|sag ?ol(un)?|eyvallah|thanks|thank you|harika|super|tamam|ok(ey)?)\b')
IDENT = re.compile(r'(sen kimsin|kimsin|adin ne|ismin ne|kendini tanit|seni kim (yapti|gelistirdi|yarat)|hangi (yapay zeka|model)|'
                   r'gemini misin|chatgpt misin|google mi|openai|who are you|your name|nesin\b)')
TIME_Q = re.compile(r'(saat kac|bugun (gunlerden|ayin|tarih|ne(\s|$))|bugunun tarihi|hangi gundeyiz|tarih ne|bugun hangi gun|ayin kaci|what time|today.s date)')
LIVE = re.compile(r'(fiyat|kac (tl|lira|dolar|euro)|doviz|kur\b|dolar|euro|borsa|bitcoin|hava durumu|hava nasil|mac (skoru|sonucu)|skor|son dakika|'
                  r'haber|bugun|simdi|su an|guncel|nobetci|trafik)')
QUESTION = re.compile(r'(\?|\b(ne|neler|nedir|nelerdir|kim|kimdir|kimin|nerede|neresi|neresidir|nereden|ne zaman|kac|kactir|hangi|hangisi|'
                      r'nasil|neden|niye|mi|mu|midir|mudur|hakkinda|what|who|where|when|which|how|why)\b)')
CREATIVE = re.compile(r'\b(siir|hikaye|masal|fikra|sarki|sozler|mektup|yaz\b|yazar misin|olustur|uydur|tavsiye|oner|onerir|ipucu|fikir|'
                      r'ozetle|cevir|duzelt|kod|program yaz|plan|tarif)\b')
DEFQ = re.compile(r'(\bnedir\b|\bne demek|\bkimdir\b|\bne ise yar|\bneye yarar|\bne icin kullanilir|\bfaydalari|\bzararlari|'
                  r'\banlat|\bacikla|\bbilgi ver|\bhakkinda|\bnelerdir\b|\btanimi\b|\bbiliyor musun|\bbilir misin)')
NUMQ = re.compile(r'\b(kac|kactir|ne zaman|hangi yil|hangi tarih|yuksekligi|uzunlugu|nufusu|yuzolcumu)\b')
DAYS = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
MONTHS = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.Mod: operator.mod, ast.USub: operator.neg, ast.UAdd: operator.pos, ast.FloorDiv: operator.floordiv}


def _eval(n):
    if isinstance(n, ast.Expression):
        return _eval(n.body)
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
        return n.value
    if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
        if isinstance(n.op, ast.Pow) and abs(_eval(n.right)) > 100:
            raise ValueError('too big')
        return _OPS[type(n.op)](_eval(n.left), _eval(n.right))
    if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
        return _OPS[type(n.op)](_eval(n.operand))
    raise ValueError('bad expr')


def arithmetic(text):
    t = fold(text).replace('x', '*').replace('×', '*').replace('÷', '/').replace(',', '.')
    t = re.sub(r'\b(arti)\b', '+', t); t = re.sub(r'\b(eksi)\b', '-', t)
    t = re.sub(r'\b(carpi)\b', '*', t); t = re.sub(r'\b(bolu)\b', '/', t)
    m = re.search(r'[-+(]?\s*\d[\d\s.+\-*/%()^]*\d\)?', t)
    if not m or not re.search(r'\d\s*[-+*/%^]\s*\(?\s*\d', m.group(0)):
        return None
    expr = m.group(0).replace('^', '**')
    try:
        v = _eval(ast.parse(expr, mode='eval'))
    except Exception:
        return None
    if isinstance(v, float):
        v = round(v, 10)
        if v.is_integer():
            v = int(v)
    shown = expr.replace('**', '^').strip()
    vs = f'{v:,}'.replace(',', '#').replace('.', ',').replace('#', '.') if isinstance(v, int) else str(v).replace('.', ',')
    return f'{shown} = **{vs}**'


def now_text():
    n = datetime.datetime.now(TZ)
    return f'{n.day} {MONTHS[n.month - 1]} {n.year} {DAYS[n.weekday()]}, saat {n:%H:%M} (Türkiye saati)'


def classify(text):
    f = fold(text).strip()
    f1 = re.sub(r'[^0-9a-z\s?]', ' ', f)
    words = f1.split()
    if IDENT.search(f1):
        return 'identity'
    if TIME_Q.search(f1):
        return 'time'
    if arithmetic(text):
        return 'math'
    if GREET.match(f1) and len(words) <= 4 and not QUESTION.search(' '.join(words[1:]) if len(words) > 1 else ''):
        return 'greet'
    if THANKS.match(f1) and len(words) <= 4:
        return 'thanks'
    if DEFQ.search(f1) and not re.search(r'\b(siir|hikaye|masal|fikra|sarki|mektup|kod)\b', f1):
        return 'factual'
    if CREATIVE.search(f1) and not re.search(r'\b(nedir|kimdir|ne zaman|nerede|kac)\b', f1):
        return 'creative'
    if QUESTION.search(f1) or len(Q(text).terms) >= 1 and len(words) <= 6:
        return 'factual'
    return 'creative'


def resolve_followup(text, prev_user):
    """'Peki nüfusu kaç?' after 'Ankara nerede?' -> search with the previous topic as context."""
    if not prev_user:
        return text
    terms = Q(text).terms
    has_proper = any(t.cap for t in terms)
    if not has_proper and len(text.split()) <= 6 and re.search(r'\b(peki|onun|bunun|onu|orasi|oranin|o\b|nufusu|baskenti|ne zaman|nerede|kac)', fold(text)):
        pt = Q(prev_user).terms
        keep = [t.surf for t in pt if t.cap] or [t.surf for t in pt][:2]
        return (' '.join(keep) + "'in " + text) if keep else text
    return text


class Answer:
    def __init__(self, kind, text=None, sources=None, stream=None):  # noqa
        self.kind, self.text, self.sources, self.stream = kind, text, sources or [], stream


class Brain:
    def __init__(self, index, lm):
        self.ix, self.lm = index, lm

    def answer(self, messages, web_sources=None, temperature=0.7):
        users = [m for m in messages if m.get('role') == 'user']
        if not users:
            return Answer('smalltalk', 'Merhaba! Ben Alper AI. Ne sormak istersin?')
        q = _text(users[-1].get('content'))
        prev = _text(users[-2].get('content')) if len(users) > 1 else ''
        kind = classify(q)
        greet_prefix = 'Merhaba! ' if GREET.match(fold(q)) and kind not in ('greet',) else ''

        if kind == 'identity':
            return Answer('identity', 'Ben **Alper AI**. Yusuf Alper tarafından sıfırdan geliştirildim: kendi tokenizer\'ım, '
                                      'kendi dil modelim ve kendi Vikipedi arama dizinimle çalışıyorum. Gemini, ChatGPT ya da '
                                      'başka bir şirketin modeli değilim.')
        if kind == 'time':
            return Answer('time', f'Şu an **{now_text()}**.')
        if kind == 'math':
            return Answer('math', arithmetic(q))
        if kind == 'greet':
            f = fold(q)
            if 'nasilsin' in f or 'naber' in f:
                return Answer('smalltalk', 'İyiyim, teşekkür ederim! Sana nasıl yardımcı olabilirim?')
            if 'gunaydin' in f:
                return Answer('smalltalk', 'Günaydın! Bugün ne öğrenmek ya da yapmak istersin?')
            if 'iyi geceler' in f:
                return Answer('smalltalk', 'İyi geceler! Yarın görüşmek üzere.')
            return Answer('smalltalk', random.choice(['Merhaba! Ben Alper AI. Sana nasıl yardımcı olabilirim?',
                                                      'Selam! Ne sormak istersin?']))
        if kind == 'thanks':
            return Answer('smalltalk', 'Rica ederim! Başka bir sorun olursa buradayım.')
        if kind == 'factual':
            return self._factual(q, resolve_followup(q, prev), web_sources, greet_prefix)
        return self._creative(messages, temperature)

    # ---- factual: only copy from sources
    def _factual(self, q, query, web_sources, prefix):
        live_q = bool(LIVE.search(fold(q)))
        fq = fold(q)
        # 1) definition-style questions ("BCAA nedir", "kreatin anlat"): live Turkish Wikipedia lead, typo/synonym-fixed
        if DEFQ.search(fq) and not live_q:
            try:
                hit = livekb.lookup(query)
            except Exception:
                hit = None
            if hit:
                return Answer('wiki', prefix + hit['text'], hit['sources'])
        res = self.ix.answer(query) if self.ix else {'confident': False}
        if not res.get('confident'):
            # 2) not in our index: rank sentences from live Wikipedia full texts + web snippets with our own rules
            try:
                extra = livekb.context_sources(query)
            except Exception:
                extra = []
            if NUMQ.search(fq):
                units = [u for u in ('metre', 'kilometre', 'km', 'kg', 'derece', 'nufus', 'yil', 'yuzyil') if re.search(r'\b' + u, fq)]
                def ok(x):
                    fx = fold(x)
                    if not re.search(r'\d', x):
                        return False
                    if 'ne zaman' in fq or 'hangi yil' in fq:
                        return bool(re.search(r'\b1\d{3}|\b20\d{2}|\b\d{1,2}\s+(ocak|subat|mart|nisan|mayis|haziran|temmuz|agustos|eylul|ekim|kasim|aralik)', fx))
                    return all(re.search(r'\d[\d.,]*\s*' + u, fx) for u in units if u in ('metre', 'kilometre', 'km', 'kg', 'derece'))
                extra = [{**e, 'snippet': ' '.join(x for x in livekb.SENT.split(e['snippet']) if ok(x))} for e in extra]
            web_sources = list(web_sources or []) + extra
            if DEFQ.search(fq) and not res.get('doc'):
                try:
                    hit = livekb.lookup(query)
                except Exception:
                    hit = None
                if hit:
                    return Answer('wiki', prefix + hit['text'], hit['sources'])
        ext = score_external(query, web_sources)
        live = live_q
        sources, parts = [], []

        def cite(src):
            for i, s in enumerate(sources):
                if s['url'] == src['url']:
                    return i + 1
            sources.append(src)
            return len(sources)

        doc = res.get('doc')
        ext_full = [(s, sent) for c, s, sent in ext if c >= 1.0]
        if res.get('confident') and not live:
            sent = render(res)
            n = cite({'title': f"Vikipedi: {doc['title']}", 'url': doc['url'], 'snippet': res['sentence'][:300], 'origin': 'alper-wiki'})
            parts.append(f'{sent} [{n}]')
            for s, sx in ext_full[:1]:
                if _similar(sx, res['sentence']):
                    continue
                n3 = cite({**s, 'origin': s.get('origin', 'web')})
                parts.append(f"Web kaynağı da şunu söylüyor: {_clip(sx)} [{n3}]")
            return Answer('wiki', prefix + '\n\n'.join(parts), sources)
        if ext_full:
            body = []
            for s, sx in ext_full[:2]:
                n = cite({**s, 'origin': s.get('origin', 'web')})
                body.append(f"{_clip(sx)} [{n}]")
            lead = 'Güncel web kaynaklarına göre:' if live else 'Bulduğum kaynaklara göre:'
            return Answer('web', prefix + lead + '\n\n' + '\n\n'.join(body) +
                          '\n\n_Bu bilgi web kaynaklarından aynen aktarılmıştır; önemli kararlar için kaynağı kontrol et._', sources)
        if live:
            return Answer('unsure', prefix + f'{UNSURE} Bu soru **güncel** bir bilgi istiyor (fiyat, kur, hava, haber, skor gibi). '
                                             'Kendi Vikipedi dizinim güncel verileri içermiyor; uygulamada **Web\'de doğrula** açıkken '
                                             'web kaynaklarından bakabilirim.')
        # the topic article was found but not the asked detail: show its lead, clearly marked as not an answer
        if doc and res.get('sentence'):
            n = cite({'title': f"Vikipedi: {doc['title']}", 'url': doc['url'], 'snippet': res['sentence'][:300], 'origin': 'alper-wiki'})
            return Answer('unsure', prefix + f'{UNSURE} Sorunun tam cevabını kaynaklarımda doğrulayamadım. '
                                             f'Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı):\n\n> {res["sentence"]} [{n}]', sources)
        ext_part = [(s, sx) for c, s, sx in ext if c >= 0.5 and sx and s.get('origin') not in ('web', 'wikipedia-live')]
        if ext_part:
            s, sx = ext_part[0]
            n = cite({**s, 'origin': s.get('origin', 'web')})
            return Answer('unsure', prefix + f"{UNSURE} Kesin bir cevap bulamadım; en yakın kaynak şunu söylüyor:\n\n> {_clip(sx)} [{n}]", sources)
        return Answer('unsure', prefix + f'{UNSURE} Bu konuda güvenilir bir kaynak bulamadım, bu yüzden tahmin yürütmek istemiyorum. '
                                         'Soruyu biraz farklı ya da daha ayrıntılı sorabilir misin?')

    # ---- creative / chit-chat: our own model, labelled
    def _creative(self, messages, temperature):
        turns, pending = [], None
        for m in messages:
            if m.get('role') == 'user':
                if pending is not None:
                    turns.append((pending, None))
                pending = _text(m.get('content'))
            elif m.get('role') == 'assistant' and pending is not None:
                turns.append((pending, _strip_note(_text(m.get('content')))[:400]))
                pending = None
        if pending is not None:
            turns.append((pending, None))
        turns = turns[-3:]
        if self.lm is None:
            return Answer('unsure', 'Şu an serbest metin üretemiyorum (model yüklenmedi). Bilgi sorularını yine de cevaplayabilirim.')
        out = ''
        try:
            for d in self.lm.stream(turns, temp=max(0.2, min(0.8, temperature)), cancel=None):
                out += d
                if len(out) > 700:
                    break
        except Exception:
            out = ''
        if _junk(out):
            return Answer('unsure', 'Bu tür serbest/yaratıcı metinlerde henüz iyi değilim: kendi küçük modelim hâlâ gelişiyor ve '
                                    'saçma bir şey yazmak yerine dürüst olmayı tercih ediyorum. Bilgi sorularında çok daha iyiyim; '
                                    'örneğin "Kreatin nedir?", "BCAA ne işe yarar?" ya da "Atatürk kimdir?" diye sorabilirsin.')
        return Answer('lm', out.strip() + LM_NOTE)


def _junk(t):
    t = (t or '').strip()
    if len(t) < 15:
        return True
    letters = sum(c.isalpha() for c in t)
    if letters / max(1, len(t)) < 0.7:
        return True
    if re.search(r'(.{1,4})\1{4,}', t):
        return True
    words = re.findall(r'\w+', t)
    return len(words) < 4 or len(set(words)) / len(words) < 0.4


LM_NOTE = '\n\n_— Alper Çekirdek (sıfırdan eğitilmiş deneysel model) yazdı; bilgi kaynağı olarak kullanma._'


def _strip_note(t):
    return t.split('\n\n_— Alper Çekirdek')[0]


def _similar(a, b):
    wa, wb = set(fold(a).split()), set(fold(b).split())
    return bool(wa and wb) and len(wa & wb) / max(1, min(len(wa), len(wb))) > 0.6


def _clip(s, n=420):
    s = ' '.join((s or '').split())
    return s if len(s) <= n else s[:n].rsplit(' ', 1)[0] + '…'


def _text(c):
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return ' '.join(p.get('text', '') for p in c if isinstance(p, dict))
    return str(c or '')
