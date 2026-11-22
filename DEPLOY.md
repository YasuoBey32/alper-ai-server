# Alper AI — ücretsiz sunucu (Render free web service)

Bu depo yalnızca **kod** içerir. Büyük dosyalar (kendi modelimiz `alper.npz` / `alper.pt`, tokenizer ve
Türkçe Vikipedi BM25 dizini `wiki.db`, ~1,6 GB) herkese açık HF veri deposunda durur:
https://huggingface.co/datasets/Yasuo850k/alper-ai-data — Docker imajı derlenirken `fetch_data.py` indirir.

* Model çıkarımı **numpy** ile yapılır (torch yok, RAM ≈140 MB; torch sürümüyle logit farkı < 4e-5). Eski torch sürümü: `lm_torch.py`.
* Uç noktalar: `GET /health`, `GET /v1/models`, `POST /v1/chat/completions` (OpenAI uyumlu, SSE akış).
* `ALPER_API_KEY` ortam değişkeni ayarlanırsa `Authorization: Bearer <anahtar>` zorunludur.
* Ücretsiz Render servisi 15 dk boşta kalınca uyur; ilk istek ~1 dk sürebilir.
