<div align="center">

# 🤖 Alper AI — Sunucu

### 🇹🇷 Yerli yapay zeka — Yusuf Alper tarafından sıfırdan geliştirildi

*"Görünmeyeni gören, frekansı okuyan, sistemi saldırgandan önce anlayan bir zihin."*

![Yerli](https://img.shields.io/badge/%F0%9F%87%B9%F0%9F%87%B7-Yerli%20%26%20Milli-E30A17?style=for-the-badge)
![Model](https://img.shields.io/badge/Model-S%C4%B1f%C4%B1rdan%20GPT%20(6%2C9M)-6f42c1?style=for-the-badge)
![3. taraf model](https://img.shields.io/badge/3.%20taraf%20model-YOK-success?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-SSE%20Ak%C4%B1%C5%9F-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Render](https://img.shields.io/badge/Render-Ücretsiz-46E3B7?style=for-the-badge&logo=render&logoColor=white)

</div>

---

## ✨ Nedir?

**Alper AI**, Android uygulaması *Alper AI*'ın çevrimiçi beynidir. Gemini, ChatGPT, Llama, Qwen… **hiçbirini kullanmaz.**
Tokenizer'ından dil modeline, arama motorundan cevap bulucusuna kadar her parça **sıfırdan, bizim tarafımızdan** yazıldı ve eğitildi.

> 🎯 İlke: **Yanlış cevap vermektense "Bundan emin değilim" demek.** Bilgi cevapları her zaman kaynak cümlenin aynısıdır ve kaynağı gösterilir.

## 🧠 Mimari

```
 📱 Alper AI (Android)
        │  OpenAI uyumlu istek (SSE akış)
        ▼
 ⚡ FastAPI  ──►  🧭 Beyin (brain.py) ── soru türünü ayırır
                     ├── 👋 Selam / kimlik / saat / hesap   → kurallı şablonlar
                     ├── 📚 Bilgi sorusu  → 🔎 Kendi Vikipedi aramamız (BM25, SQLite FTS5)
                     │                     → ✅ qa.py: kaynak cümleyi AYNEN aktarır
                     └── ✍️ Serbest metin → 🤖 Alper Çekirdek (sıfırdan GPT)
```

| 🧩 Parça | 🔧 Ne | 📂 Dosya |
|---|---|---|
| 🔤 **Kendi tokenizer'ımız** | Türkçe için sıfırdan eğitilmiş BPE | `model/tokenizer.json` |
| 🤖 **Alper Çekirdek** | Sıfırdan eğitilmiş GPT, 6,9 M parametre; sunucuda **numpy** ile çalışır (torch yok, ~140 MB RAM) | `model.py`, `lm.py`, `lm_torch.py` |
| 🔎 **Kendi arama motorumuz** | Türkçe Vikipedi üzerinde BM25 (SQLite FTS5) — 534 bin makale, 1,37 M pasaj | `build_index.py`, `sqlite_index.py` |
| ✅ **Soru-cevap** | Kurallı cevap bulucu (uygulamadaki çevrimdışı Java sürümüyle birebir aynı: 489/489) | `qa.py` |
| 🧭 **Beyin** | Yönlendirme, güven eşiği, "emin değilim" | `brain.py` |
| 🌐 **API** | `POST /v1/chat/completions` (SSE), `GET /v1/models`, `GET /health` | `app.py` |

📊 **Değerlendirme (v4.1):** 69 soruda 55 doğru · 14 "emin değilim" · **0 yanlış** — ayrıntılar: [`EVAL_RESULTS.md`](EVAL_RESULTS.md)

## 🚀 Çalıştırma

### ☁️ Render (ücretsiz)
Bu depo Render'a doğrudan bağlanır (`Dockerfile`). Büyük dosyalar (model + 1,6 GB Vikipedi dizini) herkese açık
🤗 [Yasuo850k/alper-ai-data](https://huggingface.co/datasets/Yasuo850k/alper-ai-data) deposundan imaj derlenirken indirilir.

> 😴 Ücretsiz sunucu 15 dk boşta kalınca uyur; ilk istek ~1 dakika sürebilir.

### 💻 Yerelde
```bash
pip install -r requirements.txt
python fetch_data.py                     # model + Vikipedi dizinini indirir
uvicorn app:app --port 10000
```

### 🧪 Dene
```bash
curl -N -H 'Content-Type: application/json' \
  -d '{"stream":true,"messages":[{"role":"user","content":"Türkiye'\''nin başkenti neresi?"}]}' \
  http://localhost:10000/v1/chat/completions
```
İsteğe bağlı: `ALPER_API_KEY` ayarlanırsa `Authorization: Bearer <anahtar>` gerekir.

## 📜 Lisans notu
Vikipedi içeriği CC BY-SA 4.0'dır; bu yüzden cevaplarda kaynak bağlantısı her zaman verilir.

---

<div align="center">

### 👨‍💻 Geliştirici: **Yusuf Alper**

*"Disiplinle şekillenen, merakla büyüyen bir mühendislik zihni."*

[![Site](https://img.shields.io/badge/🌐-yusufalper.com.tr-0A66C2?style=flat-square)](https://yusufalper.com.tr)
[![GitHub](https://img.shields.io/badge/GitHub-YasuoBey32-181717?style=flat-square&logo=github)](https://github.com/YasuoBey32)
[![Instagram](https://img.shields.io/badge/Instagram-yyusufalp32-E4405F?style=flat-square&logo=instagram&logoColor=white)](https://instagram.com/yyusufalp32)
[![Telegram](https://img.shields.io/badge/Telegram-yyusufalp32-26A5E4?style=flat-square&logo=telegram&logoColor=white)](https://t.me/yyusufalp32)

📱 Tüm uygulamalarım: [YasuoBey32/alper-apps](https://github.com/YasuoBey32/alper-apps)

</div>
