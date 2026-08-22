FROM python:3.13-slim-bookworm

ARG BRSCAN4_URL=https://download.brother.com/welcome/dlf105200/brscan4-0.4.11-1.amd64.deb
ARG BRSCAN4_SHA256=027b73648722ac8c8eb1a9c419d284a6562cc763feac9740a2b75a683b092972

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates curl gosu sane-utils \
    && curl --fail --location --silent --show-error "$BRSCAN4_URL" --output /tmp/brscan4.deb \
    && echo "$BRSCAN4_SHA256  /tmp/brscan4.deb" | sha256sum --check - \
    && apt-get install --yes --no-install-recommends /tmp/brscan4.deb \
    && rm -f /tmp/brscan4.deb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY scanner/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY scanner/server.py /app/server.py
COPY scanner/entrypoint.sh /usr/local/bin/scanner-entrypoint
RUN chmod 0755 /usr/local/bin/scanner-entrypoint

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TMPDIR=/work \
    WORK_DIR=/work \
    STATE_DIR=/state \
    SCANS_DIR=/scans

EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/scanner-entrypoint"]
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "--timeout", "1200", "--access-logfile", "-", "server:app"]
