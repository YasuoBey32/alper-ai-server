"""Alper AI server: OpenAI-compatible /v1/chat/completions (streaming SSE) backed only by our own components.

Env: ALPER_API_KEY (shared secret; if set, required as 'Authorization: Bearer <key>' or 'X-Alper-Key: <key>'),
     WIKI_DB (default data/wiki.db), MODEL_PATH (model/alper.pt), TOKENIZER_PATH (model/tokenizer.json), PORT (7860)
"""
import asyncio, hmac, json, os, threading, time, uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from brain import Brain
from sqlite_index import SqliteIndex
from qa import QA

API_KEY = os.environ.get('ALPER_API_KEY', '')
WIKI_DB = os.environ.get('WIKI_DB', 'data/wiki.db')
MODEL_PATH = os.environ.get('MODEL_PATH', 'model/alper.npz')
TOK_PATH = os.environ.get('TOKENIZER_PATH', 'model/tokenizer.json')
MODEL_NAME = 'alper-ai'

app = FastAPI(title='Alper AI', version='4.2')
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['GET', 'POST', 'OPTIONS'], allow_headers=['*'])
state = {'index': None, 'lm': None, 'errors': []}


def _load():
    try:
        if os.path.exists(WIKI_DB):
            import sqlite3
            c = sqlite3.connect(f'file:{WIKI_DB}?mode=ro&immutable=1', uri=True)   # read-only: a read-write open copies the 1.6 GB file into RAM-backed storage on Render (OOM)
            has_ttl = c.execute("SELECT name FROM sqlite_master WHERE name='ttl'").fetchone()
            c.close()
            if not has_ttl:   # v4.2.1: the title table is built into the image (Dockerfile); never at startup (OOM on 512 MB)
                state['errors'].append('wiki: ttl table missing (rebuild image)')
            state['index'] = QA(SqliteIndex(WIKI_DB))
        else:
            state['errors'].append(f'wiki index missing: {WIKI_DB}')
    except Exception as e:  # pragma: no cover
        state['errors'].append(f'wiki: {e}')
    try:
        from lm import AlperLM
        state['lm'] = AlperLM(MODEL_PATH, TOK_PATH)
    except Exception as e:
        state['errors'].append(f'model: {e}')


_load()
brain = Brain(state['index'], state['lm'])


def _warm():
    # v4.2.3: touch the title index and FTS pages once so the first real questions are fast
    for q in ('Türkiye başkenti neresi', 'Bursa nüfusu kaç', 'Atatürk kimdir', 'İstanbul ne zaman fethedildi'):
        try:
            state['index'] and state['index'].answer(q)
        except Exception:
            pass


threading.Thread(target=_warm, daemon=True).start()


def _authorized(req: Request) -> bool:
    if not API_KEY:
        return True
    got = req.headers.get('x-alper-key') or ''
    auth = req.headers.get('authorization') or ''
    if auth.lower().startswith('bearer '):
        got = got or auth[7:].strip()
    return hmac.compare_digest(got.encode(), API_KEY.encode())


def _err(status, msg, code):
    return JSONResponse({'error': {'message': msg, 'type': code, 'code': code}}, status_code=status)


@app.get('/')
@app.get('/health')
def health():
    lm = state['lm']
    return {'status': 'ok', 'name': 'Alper AI', 'version': '4.3', 'model': MODEL_NAME, 'live_wikipedia': True,
            'wiki_index': state['index'] is not None,
            'core_model': None if lm is None else {'params': lm.params, 'ctx': lm.cfg.ctx, 'layers': lm.cfg.layers, 'd': lm.cfg.d},
            'auth': bool(API_KEY), 'errors': state['errors']}


@app.get('/v1/models')
def models(req: Request):
    if not _authorized(req):
        return _err(401, 'Geçersiz ya da eksik API anahtarı.', 'invalid_api_key')
    return {'object': 'list', 'data': [{'id': MODEL_NAME, 'object': 'model', 'owned_by': 'yusuf-alper'}]}


@app.post('/v1/chat/completions')
async def chat(req: Request):
    if not _authorized(req):
        return _err(401, 'Geçersiz ya da eksik API anahtarı.', 'invalid_api_key')
    try:
        body = await req.json()
    except Exception:
        return _err(400, 'Geçersiz JSON.', 'invalid_request_error')
    messages = body.get('messages') or []
    if not isinstance(messages, list) or not messages:
        return _err(400, "'messages' gerekli.", 'invalid_request_error')
    web = body.get('alper_sources') or []
    temp = float(body.get('temperature', 0.7) or 0.7)
    stream = bool(body.get('stream'))
    cid, created = 'chatcmpl-' + uuid.uuid4().hex[:24], int(time.time())
    ans = await _answer_fast(messages, web, temp)
    meta = {'kind': ans.kind, 'sources': ans.sources}

    if not stream:
        text = ans.text if ans.stream is None else ''.join(ans.stream(None)) + (ans.text or '')
        return {'id': cid, 'object': 'chat.completion', 'created': created, 'model': MODEL_NAME, 'alper': meta,
                'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': text}, 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}}

    def chunk(delta, finish=None, extra=None):
        d = {'id': cid, 'object': 'chat.completion.chunk', 'created': created, 'model': MODEL_NAME,
             'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}
        if extra:
            d.update(extra)
        return 'data: ' + json.dumps(d, ensure_ascii=False) + '\n\n'

    async def gen():
        yield chunk({'role': 'assistant', 'content': ''}, extra={'alper': meta})
        if ans.stream is None:
            # fixed text: stream it word by word so the client shows the same typing effect
            for piece in _pieces(ans.text or ''):
                if await req.is_disconnected():
                    return
                yield chunk({'content': piece})
                await asyncio.sleep(0.004)
        else:
            cancel = threading.Event()
            q: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_running_loop()

            def work():
                try:
                    for d in ans.stream(cancel):
                        loop.call_soon_threadsafe(q.put_nowait, d)
                except Exception as e:  # pragma: no cover
                    loop.call_soon_threadsafe(q.put_nowait, f'\n\n(Hata: {e})')
                loop.call_soon_threadsafe(q.put_nowait, None)

            threading.Thread(target=work, daemon=True).start()
            while True:
                d = await q.get()
                if d is None:
                    break
                if await req.is_disconnected():
                    cancel.set(); return
                yield chunk({'content': d})
            if ans.text:
                yield chunk({'content': ans.text})
        yield chunk({}, finish='stop')
        yield 'data: [DONE]\n\n'

    return StreamingResponse(gen(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


BUDGET = float(os.environ.get('ALPER_BUDGET', '3.0'))   # v4.2.2: every answer starts within ~3 s


async def _answer_fast(messages, web, temp):
    """Run the full pipeline, and in parallel a quick live-Wikipedia lookup. If the full pipeline is not done
    within BUDGET seconds, answer with the quick result (or an honest 'not sure') instead of making the user wait."""
    import live as livekb
    from brain import Answer, _text, rewrite
    full = asyncio.ensure_future(asyncio.to_thread(brain.answer, messages, web, temp))
    users = [m for m in messages if m.get('role') == 'user']
    q = rewrite(_text(users[-1].get('content'))) if users else ''
    quick = asyncio.ensure_future(asyncio.to_thread(lambda: livekb.infobox_fact(q) or livekb.lookup(q))) if q else None
    t0 = time.monotonic()
    try:
        return await asyncio.wait_for(asyncio.shield(full), BUDGET)
    except asyncio.TimeoutError:
        pass
    except Exception:
        full = None
    hit = None
    if quick is not None:
        try:
            hit = await asyncio.wait_for(asyncio.shield(quick), max(0.3, 4.4 - (time.monotonic() - t0)))   # v4.3.2: hard cap ~4.5 s
        except Exception:
            hit = None
    if hit:
        return Answer('wiki', hit['text'], hit['sources'])
    from brain import classify
    if q and classify(q) == 'creative':
        return Answer('unsure', 'Şiir, hikâye gibi serbest metinlerde henüz iyi değilim: kendi küçük modelim hâlâ gelişiyor ve '
                                'saçma bir şey yazmak yerine dürüst olmayı tercih ediyorum. Bilgi sorularında çok daha iyiyim.')
    return Answer('unsure', 'Bundan emin değilim. Bu soruyu birkaç saniyede kaynaklarımda doğrulayamadım; '
                            'soruyu biraz daha açık yazarsan (örneğin "Bursa nüfusu kaç") daha hızlı bulurum.')


def _pieces(t):
    import re
    return re.findall(r'\S+\s*|\s+', t)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', '7860')))
