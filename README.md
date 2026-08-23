# Print & Scan Hub

Print & Scan Hub is a self-hosted, beginner-friendly web interface for household printing, DYMO label creation, and searchable document scanning. The browser is the only interface a user needs.

## Features

- Print a PDF from the browser
- Automatically print complete PDFs copied into a shared hotfolder
- Choose between configured document printers
- Create DYMO labels in a rich-text editor
- Paste images into labels, preview, save, reopen, copy, and delete them
- Scan front sides or use the guided front/back workflow
- Scan in document gray or full color
- Produce downloadable PDFs with German and English OCR
- Rename and delete scanned PDFs in the browser
- Print a saved scan on any configured document printer
- Install the HTTPS interface as a PWA on desktop and mobile devices
- Choose an English or German interface through one environment setting
- Switch between the default dark interface and a browser-persisted light mode
- Recover the original PDF and retry when OCR fails
- Restart all services automatically after failures and host reboots

The interface and documentation are entirely in English. There is deliberately no AI integration.

## Architecture

The deployment has exactly four containers:

| Service | Responsibility |
| --- | --- |
| web | Shared interface, label storage, PDF submission, and scan file management |
| cups | HP, Brother, and DYMO queues and printer drivers |
| scanner | Brother SANE driver, front/back scanning, blank-page filtering, and PDF assembly |
| ocr | Isolated OCRmyPDF and Tesseract processing in German and English |

Only the web service is published, on port **8081**. All services use restart: unless-stopped.

PDFs copied into `data/jobs` are automatically sent to
`defaultDocumentPrinter`. A file must remain unchanged for 15 seconds and pass
PDF header and end-marker checks before it is submitted, which prevents an
in-progress network copy from being printed. CUPS failures leave the PDF in the
folder for an automatic retry.

OCR has no persistent volume. Scanner and OCR working directories are separate 2 GiB tmpfs mounts, so temporary files disappear on restart and cannot grow without a fixed limit. Every OCR request uses its own temporary directory with guaranteed cleanup.

## Quick start

Requirements are Docker Engine, Docker Compose v2, Git, an amd64 Linux host, and a trusted local network.

    git clone https://github.com/YOUR-ACCOUNT/print-scan-hub.git
    cd print-scan-hub
    cp .env.example .env
    cp config/printers.json config/printers.local.json

Edit .env and config/printers.local.json, then start the stack:

    docker compose up -d --build
    docker compose ps

Open http://SERVER-IP:8081.

For an installable PWA, serve the application through HTTPS. The deployment
guide includes an anonymized Apache reverse-proxy template. Open the HTTPS URL
in a supported browser and choose **Install app** or **Add to Home Screen**.

The included public printer configuration uses documentation-only addresses. Put real addresses only in the ignored config/printers.local.json.

## Supported reference hardware

- HP Color Laser MFP 178nw via its SPL-C driver
- Brother MFC-L2710DW for printing and network scanning
- DYMO LabelWriter 450 via USB

Other printers can be configured, but scanner support is currently Brother brscan4-specific.

## Everyday scanning

Place pages in the Brother document feeder **face up, top edge first**. Choose Document for clear text and smaller files or Color to preserve colors.

For two-sided pages, scan the fronts first. When prompted, keep the pages in the same order, turn the complete stack over, place it face up and top edge first, then select Scan back sides.

Document mode uses 150 dpi True Gray. Color mode uses 150 dpi 24-bit color. OCR runs only after all pages are assembled.

## Security

This is a private-LAN appliance with no accounts. Anyone who can reach port 8081 can print, scan, rename scans, and delete scans. Do not publish it directly to the internet. See [SECURITY.md](SECURITY.md).

## Documentation

- [Deployment](docs/deployment.md)
- [Configuration](docs/configuration.md)
- [Architecture](docs/architecture.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Development](docs/development.md)
- [Third-party software](THIRD_PARTY.md)

## License

Print & Scan Hub is licensed under the [GNU General Public License v3](LICENSE).
