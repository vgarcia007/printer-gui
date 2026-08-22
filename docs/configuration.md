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
- JOBS_HOST_DIR: local or network-backed PDF hotfolder; default ./data/jobs
- HOTFOLDER_ENABLED: automatically print PDFs from JOBS_HOST_DIR; default true
- HOTFOLDER_STABLE_SECONDS: required unchanged time before printing; default 15
- HOTFOLDER_POLL_SECONDS: folder check interval; default 2
- HOTFOLDER_RETRY_SECONDS: delay after an incomplete file or print failure; default 30
- APP_UID and APP_GID: owner used for label and scan files
- SECRET_KEY: long random value used for browser CSRF protection
- DYMO_LANDSCAPE_OFFSET_MM: feed-direction correction in millimeters; default 0
- DYMO_LANDSCAPE_SHRINK_MM: optional horizontal artwork reduction; default 0
- DYMO_LANDSCAPE_START_TRIM_MM: optional leading-edge inset; default 0

The DYMO 30321 roll is nominally 89 × 36 mm. The editor uses the driver's
88 × 34 mm printable area and shows a dashed 2 mm safe margin. The default
calibration values preserve that artwork at 1:1 scale. Adjust them only after a
measured test print; a negative offset can clip content at the feed edge and a
shrink value makes printed text differ from the editor preview.

After changes, run docker compose up -d.
