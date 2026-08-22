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
ADD --checksum=sha256:99464ceb71bc9bbdcc72275faefe44f98eb5cbb6b5d8ee665b87b35376f1a96e https://raw.githubusercontent.com/FortAwesome/Font-Awesome/5.15.4/css/all.min.css /app/app/static/vendor/fontawesome/css/all.min.css
ADD --checksum=sha256:f82c17b6cba4ae53d18f40ab8066eea83ffabe9e73ce61df4034403fbcd65265 https://raw.githubusercontent.com/FortAwesome/Font-Awesome/5.15.4/webfonts/fa-regular-400.woff2 /app/app/static/vendor/fontawesome/webfonts/fa-regular-400.woff2
ADD --checksum=sha256:1d0e6c7f6b40b62c10c929739ed76b0adbd9a08591aa95697b6f802c4dc4824f https://raw.githubusercontent.com/FortAwesome/Font-Awesome/5.15.4/webfonts/fa-solid-900.woff2 /app/app/static/vendor/fontawesome/webfonts/fa-solid-900.woff2
ADD --checksum=sha256:e779748dfe75e84f974df3c7bc07f842011a100159158b0f1f49b2f2a5a515cb https://raw.githubusercontent.com/FortAwesome/Font-Awesome/5.15.4/LICENSE.txt /app/app/static/vendor/fontawesome/LICENSE.txt
RUN find /app/app/static/vendor/fontawesome -type f -exec chmod 0644 {} + \
    && chmod 0644 /app/app/static/vendor/html2canvas.min.js
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
