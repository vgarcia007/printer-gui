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
ADD --checksum=sha256:b164a2d2905748e1d48512f1e985606b4282c9438bbc0ee2958e56f658695d2b https://raw.githubusercontent.com/FortAwesome/Font-Awesome/7.2.0/css/fontawesome.min.css /app/app/static/vendor/fontawesome/css/fontawesome.min.css
ADD --checksum=sha256:abb7189386e7601b342822b2a72812cf972daeb3442b796d7a785ea6f860f7e6 https://raw.githubusercontent.com/FortAwesome/Font-Awesome/7.2.0/css/solid.min.css /app/app/static/vendor/fontawesome/css/solid.min.css
ADD --checksum=sha256:f3cd581e4741affa82a791e6111a2797c075893dc3a942bb0722eb2a7caa3da1 https://raw.githubusercontent.com/FortAwesome/Font-Awesome/7.2.0/webfonts/fa-solid-900.woff2 /app/app/static/vendor/fontawesome/webfonts/fa-solid-900.woff2
ADD --checksum=sha256:20c6f40715a567c97b80f6944beb8bb325835cab47ea7dcab89ee3b8e077eced https://raw.githubusercontent.com/FortAwesome/Font-Awesome/7.2.0/LICENSE.txt /app/app/static/vendor/fontawesome/LICENSE.txt
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
