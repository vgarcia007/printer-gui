FROM python:3.13-slim-bookworm

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
       ghostscript ocrmypdf tesseract-ocr-deu tesseract-ocr-eng unpaper \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10002 --shell /usr/sbin/nologin ocr

WORKDIR /app
COPY ocr/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY ocr/server.py /app/server.py

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TMPDIR=/work \
    WORK_DIR=/work

USER ocr
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "2", "--timeout", "1200", "--access-logfile", "-", "server:app"]
