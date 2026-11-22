# Alper AI server — Render free web service (512 MB RAM). Stable launcher: the code and data come from the public
# HF dataset Yasuo850k/alper-ai-data, so a redeploy is "upload to HF + Render deploy hook" (see deploy.sh).
#   code.tar.gz          : server code (app.py, brain.py, qa.py, …; numpy inference lm.py, no torch)
#   alper.npz, tokenizer : our from-scratch GPT ;  wiki.db : our SQLite FTS5 index over Turkish Wikipedia
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PORT=10000 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
    ALPER_DATA_REPO=Yasuo850k/alper-ai-data
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt
ARG HFB=https://huggingface.co/datasets/Yasuo850k/alper-ai-data/resolve/main
# changing data_version.txt on HF re-downloads the index; otherwise this layer stays cached
ADD ${HFB}/data_version.txt /app/data_version.txt
RUN mkdir -p data && python -c "import urllib.request as u; u.urlretrieve('${HFB}/wiki.db', 'data/wiki.db')" && ls -la data
# changing code_version.txt on HF re-downloads code + model
ADD ${HFB}/code_version.txt /app/code_version.txt
RUN python -c "import urllib.request as u; u.urlretrieve('${HFB}/code.tar.gz', '/tmp/code.tgz')" && \
    tar xzf /tmp/code.tgz -C /app && rm /tmp/code.tgz && python fetch_data.py && cat code_version.txt
EXPOSE 10000
CMD ["sh", "-c", "python fetch_data.py && exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
