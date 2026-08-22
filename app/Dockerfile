FROM python:3.13-slim-bookworm

RUN apt-get update \
    && apt-get install --yes --no-install-recommends cups-client gosu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY config.py run.py /app/
COPY app /app/app
ADD --checksum=sha256:e87e550794322e574a1fda0c1549a3c70dae5a93d9113417a429016838eab8cb https://github.com/niklasvh/html2canvas/releases/download/v1.4.1/html2canvas.min.js /app/app/static/vendor/html2canvas.min.js
RUN chmod 0644 /app/app/static/vendor/html2canvas.min.js
COPY label_templates /app/label_templates
COPY tests /app/tests
COPY app/entrypoint.sh /usr/local/bin/print-scan-hub-entrypoint
RUN chmod 0755 /usr/local/bin/print-scan-hub-entrypoint

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LC_ALL=C.UTF-8

EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/print-scan-hub-entrypoint"]
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "120", "--access-logfile", "-", "run:app"]
