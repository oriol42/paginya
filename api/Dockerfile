# Paginya API — Render (free plan: 512 MB, 0.1 CPU). Build context: api/
FROM python:3.12-slim-bookworm
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      libreoffice-writer-nogui python3-uno tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng poppler-utils ghostscript \
      fonts-liberation2 fonts-crosextra-carlito fonts-crosextra-caladea fonts-dejavu libglib2.0-0 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt "psycopg[binary]>=3.2"
COPY app ./app
COPY fonts ./fonts
ENV PROPRE_DATA_DIR=/tmp/data PROPRE_UNO_PYTHON=/usr/bin/python3 HOME=/tmp PYTHONUNBUFFERED=1
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1 --proxy-headers --forwarded-allow-ips '*'"]
