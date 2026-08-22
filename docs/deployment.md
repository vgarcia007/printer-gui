# Deployment

## Requirements

- A Debian Linux host on the same network as the printers
- Docker Engine with the Compose v2 plugin
- Git
- About 1 GB of free disk space for images and persistent data
- TCP access from the server to the printer endpoints

No Python, CUPS, or printer driver needs to be installed on the host.

## Install

```bash
git clone git@github.com:vgarcia007/printer-gui.git
cd printer-gui
docker compose up -d --build
```

Wait until both services are healthy:

```bash
docker compose ps
```

Open `http://SERVER-IP:8080`. The page is available to every device that can reach that address; there is deliberately no login screen.

## Port and environment settings

Port 8080 is the default. To choose another host port, create `.env`:

```dotenv
WEB_PORT=8090
```

Then run `docker compose up -d`. CUPS port 631 is not published to the host.

## Persistent data

All application state stays below the cloned directory:

| Path | Purpose |
| --- | --- |
| `config/printers.json` | Portable printer definitions |
| `data/jobs` | PDFs waiting to be printed |
| `data/cups` | Generated CUPS configuration and queue state |
| `data/spool` | CUPS spool data |

Back up the entire directory, or at least `config` and `data`. Stop the stack before restoring CUPS state.

## Updates

Review local changes first, then update and rebuild:

```bash
git pull --ff-only
docker compose up -d --build
```

The containers use `restart: unless-stopped`, so Docker starts them again after a host reboot.

## Trusted-network boundary

Anyone who can reach the web port can submit a PDF to either configured printer. Do not expose this service directly to the internet. If access beyond a trusted LAN is required, place an authenticated HTTPS reverse proxy or VPN in front of it.
