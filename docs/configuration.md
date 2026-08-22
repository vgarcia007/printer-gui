# Configuration

Copy the public templates before deployment:

    cp config/printers.json config/printers.local.json
    cp .env.example .env

Real device addresses belong only in these ignored local files.

## Printer schema

Schema version 2 assigns each printer a kind of document or label. defaultDocumentPrinter selects the initial document queue and labelPrinter identifies the DYMO queue.

The name is a safe CUPS queue name, label is user-facing text, uri is the device URI, driver is a CUPS model identifier, and options contains queue defaults.

Inspect available devices and models with:

    docker compose exec cups lpinfo -v
    docker compose exec cups lpinfo -m
    docker compose exec cups lpstat -p -d

## Environment

Important .env values:

- WEB_PORT: host port, default 8081
- SCANNER_IP: Brother scanner address
- SCANNER_MODEL: brscan4 model identifier; MFC-L2700DW is compatible with the reference device
- SCANS_HOST_DIR: final PDF directory or NAS mount
- APP_UID and APP_GID: owner used for label and scan files
- SECRET_KEY: long random value used for browser CSRF protection

After changes, run docker compose up -d.
