# Alper AI server — free-tier build (Render free web service, 512 MB RAM). Everything served is ours:
#   model/alper.npz + tokenizer.json : our from-scratch GPT (numpy inference, no torch)
#   data/wiki.db                      : our BM25 (SQLite FTS5) index over Turkish Wikipedia
# Big files live in the public HF dataset Yasuo850k/alper-ai-data and are baked into the image at build time.
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PORT=10000 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MALLOC_ARENA_MAX=2
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ARG ALPER_DATA_REV=main
RUN ALPER_DATA_REV=${ALPER_DATA_REV} python fetch_data.py
# v4.2.1: build the title lookup table at image build time (doing it at startup ran out of memory on the free plan)
RUN python -c "import sqlite3; from add_titles import add_titles; c=sqlite3.connect('data/wiki.db'); print(add_titles(c), 'titles')"
EXPOSE 10000
# fetch_data.py again at start is a no-op when the files are baked in (fallback if the image was built without them)
CMD ["sh", "-c", "exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1 --limit-concurrency 8 --timeout-keep-alive 5"]
