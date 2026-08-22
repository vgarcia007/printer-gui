FROM python:3.13-slim-bookworm

RUN apt-get update \
    && apt-get install --yes --no-install-recommends cups-client gosu \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin printer-gui

WORKDIR /app
COPY app/server.py /app/server.py
COPY app/static /app/static
COPY app/entrypoint.sh /usr/local/bin/printer-gui-entrypoint

RUN chmod 0755 /usr/local/bin/printer-gui-entrypoint

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LC_ALL=C

EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/printer-gui-entrypoint"]
CMD ["--host", "0.0.0.0", "--port", "8080"]
