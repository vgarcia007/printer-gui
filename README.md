# Printer GUI

A small, modern web interface for household printing. It runs on a Debian Linux server with Docker Compose, discovers its configured CUPS queues, prints every PDF in a shared jobs directory, and accepts one PDF by file picker or drag and drop.

The application intentionally has no user accounts. Run it only on a trusted private network.

## Features

- One uncluttered, responsive screen
- Print all PDFs from `data/jobs`
- Select or drag and drop a single PDF
- Configurable printer dropdown
- HP Color Laser MFP 178nw selected by default
- Persistent jobs, CUPS settings, and spool data inside this repository directory
- Correct HP SPL-C filter instead of sending incompatible raw PDF data
- No database and no JavaScript framework
- `amd64` and `arm64` container builds

## Quick start

Requirements: Git, Docker Engine, and Docker Compose v2.

```bash
git clone git@github.com:vgarcia007/printer-gui.git
cd printer-gui
docker compose up -d --build
```

Open `http://SERVER-IP:8080` from a device on the same network. You can also run `make up` as a shorthand.

The included configuration contains:

| Queue | Model | Address | Driver |
| --- | --- | --- | --- |
| `hp-color` | HP Color Laser MFP 178nw | `socket://192.168.188.71` | HP 17x SPL-C (default) |
| `mfc` | Brother MFC-L2710DW | `http://192.168.188.133` | brlaser |

Change these addresses in [`config/printers.json`](config/printers.json) when using the project on a different network, then restart the stack:

```bash
docker compose up -d
```

## Everyday use

- Put any number of PDFs into `data/jobs` and use **Alle drucken** in the web interface.
- Select a PDF or drop it onto the upload area to send just that file.
- A file is deleted from the jobs directory only after CUPS accepts the print job.
- Uploaded files that cannot be printed remain in `data/jobs` for recovery.

> [!IMPORTANT]
> The HP Color Laser MFP 178nw uses Samsung Printer Language Color (SPL-C). Do not replace its configured driver with `raw` or a generic driverless queue. Incorrect print data is the reason this printer may output cryptic characters and many blank pages.

## Stack

- Python 3 standard-library HTTP server and API
- Plain HTML, CSS, and JavaScript
- CUPS for queueing and PDF conversion
- Official HP Unified Linux Driver components for the 17x series
- Docker Compose with separate `web` and `cups` services

The browser can reach only the web service on port 8080. CUPS stays on the private Compose network and can reach printers on the household LAN.

## Commands

```bash
make up          # build and start
make status      # show container health
make logs        # follow logs
make test        # run unit tests
make validate    # run all local checks
make down        # stop the stack
```

## Documentation

- [Deployment](docs/deployment.md)
- [Printer configuration](docs/configuration.md)
- [Architecture and security](docs/architecture.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Development](docs/development.md)
- [Debian validation handoff](docs/handoff.md)

## License and third-party software

This project is licensed under the [GNU General Public License v3](LICENSE).

The CUPS image is based on [`olbat/cupsd`](https://github.com/olbat/docker-cupsd). The HP Unified Linux Driver is downloaded from HP during the image build, verified by SHA-256, and is subject to HP's own license terms. It is not redistributed in this repository.
