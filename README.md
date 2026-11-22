---
title: Alper AI
emoji: 🤖
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Alper AI — sunucu (Hugging Face Space, Docker)

Alper AI uygulamasının çevrimiçi beyni. **Hiçbir üçüncü taraf dil modeli kullanmaz**:

| Parça | Ne | Nerede |
|---|---|---|
| Alper Çekirdek | Sıfırdan eğitilmiş GPT (6,9 M parametre, kendi BPE tokenizer'ı) — sohbet / serbest metin | `model/alper.pt`, `model/tokenizer.json`, `model.py`, `lm.py` |
| Bilgi dizini | Türkçe Vikipedi üzerinde kendi BM25 aramamız (SQLite FTS5, ~1,37 M pasaj) | `data/wiki.db` (`build_index.py` ile üretilir), `search.py` |
| Beyin | Soru türünü ayırır; bilgi sorularında cevabı kaynak cümleden **aynen** alır, emin değilse "Bundan emin değilim" der | `brain.py` |
| API | OpenAI uyumlu `POST /v1/chat/completions` (SSE akış), `GET /v1/models`, `GET /health` | `app.py` |

## Nasıl cevap verir

* Selam / teşekkür / "sen kimsin" / saat-tarih / aritmetik → sabit ve doğru şablonlar (tarih Europe/Istanbul).
* Bilgi sorusu → Vikipedi dizininde arama. Bir cümle (makale başlığı bağlam sayılarak) sorudaki **tüm gerekli
  kelimeleri** içermiyorsa cevap "kesin" sayılmaz. Kesinse cümle aynen aktarılır ve kaynak gösterilir; değilse
  "Bundan emin değilim." + (varsa) en ilgili alıntı açıkça "doğrulanmadı" diye işaretlenir.
* Uygulama "Web'de doğrula" açıkken kendi bulduğu canlı kaynakları `alper_sources` alanında yollar; sunucu bunları da
  aynı kurala göre değerlendirir (güncel sorular: fiyat, kur, hava, haber…).
* Serbest metin (şiir, öneri, sohbet) → Alper Çekirdek üretir ve cevabın altına "deneysel, bilgi kaynağı değil" notu eklenir.
  Model küçük olduğu için bu metinler çoğu zaman tutarsızdır; bilgi cevapları ondan **gelmez**.

## API

```
POST /v1/chat/completions
Authorization: Bearer <ALPER_API_KEY>      (ya da  X-Alper-Key: <ALPER_API_KEY>)
{"model":"alper-ai","stream":true,"temperature":0.7,
 "messages":[{"role":"user","content":"Everest Dağı'nın yüksekliği kaç metre?"}],
 "alper_sources":[{"title":"…","url":"https://…","snippet":"…"}]   // isteğe bağlı
}
```
Akışın ilk parçasında ek bir alan gelir: `"alper": {"kind": "wiki|web|unsure|lm|smalltalk|identity|time|math",
"sources": [{"title","url","snippet","origin"}]}`. Cevaptaki `[1]` gibi numaralar bu listeye karşılık gelir.
Standart OpenAI istemcileri bu alanı yok sayar.

## Hugging Face Space olarak yayınlama

1. huggingface.co → **New Space** → ad: `alper-ai` (adres `https://<kullanıcı>-alper-ai.hf.space` olur), SDK: **Docker**,
   donanım: *CPU basic (ücretsiz)* yeterli.
2. Space → **Settings → Variables and secrets → New secret**: `ALPER_API_KEY` = uzun rastgele bir parola
   (ör. `python -c "import secrets;print(secrets.token_urlsafe(32))"`).
3. Bu klasörü Space deposuna gönder (`model/alper.pt` 28 MB olduğu için git-lfs gerekir):
   ```bash
   git clone https://huggingface.co/spaces/<kullanıcı>/alper-ai && cd alper-ai
   git lfs install && git lfs track "*.pt"
   cp -r /path/to/apk/server/* /path/to/apk/server/.dockerignore .
   git add . && git commit -m "Alper AI sunucusu" && git push
   ```
4. İlk derleme ~10 dk sürer (Vikipedi dökümü indirilir ve dizin kurulur, ~1,6 GB). Bittiğinde
   `https://<kullanıcı>-alper-ai.hf.space/health` → `{"status":"ok","wiki_index":true,...}`.
5. Uygulamada **Ayarlar → Sunucu**: adresi ve `ALPER_API_KEY` değerini gir → **Bağlantıyı test et**.

Not: Ücretsiz Space'ler 48 saat kullanılmazsa uyur; ilk istekte uyanması 1-2 dakika sürebilir (uygulama bunu söyler).

## Yerelde çalıştırma

```bash
pip install -r requirements.txt
# dizin: iki Vikipedi parçasını indirip kur (≈4 dk)
python build_index.py data/wiki_0.parquet data/wiki_1.parquet --out data/wiki.db
ALPER_API_KEY=deneme uvicorn app:app --port 7860
curl -N -H 'Authorization: Bearer deneme' -H 'Content-Type: application/json' \
  -d '{"stream":true,"messages":[{"role":"user","content":"Fotosentez nedir?"}]}' localhost:7860/v1/chat/completions
```
Büyük derleme adımları zaman sınırına takılırsa `--no-finalize` / `--append` ile parça parça kurulabilir.

## Modeli güncelleme

Yeni bir eğitim checkpoint'i (`ai/ckpt_sft.pt`) için: `python export_ckpt.py ../../ai/ckpt_sft.pt model/alper.pt`.
Model boyutu (katman, genişlik, bağlam) büyüse bile yapılandırma checkpoint içindeki `cfg` alanından okunur.

Ortam değişkenleri: `ALPER_API_KEY`, `WIKI_DB` (data/wiki.db), `MODEL_PATH`, `TOKENIZER_PATH`, `TORCH_THREADS` (2), `PORT` (7860).
Vikipedi içeriği CC BY-SA 4.0 lisanslıdır; cevaplarda kaynak bağlantısı bu yüzden her zaman verilir.
