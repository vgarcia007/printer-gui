# Deployment

## Requirements

- Docker Engine and Docker Compose v2 on an amd64 Linux host
- Network access to the HP and Brother devices
- USB access to the DYMO LabelWriter
- At least 3 GiB RAM available for peak temporary processing
- A writable scan destination

Follow the README Quick start, then verify:

    docker compose ps
    curl --fail http://localhost:8081/health
    curl --fail http://localhost:8081/scans/api/status

All four services should be healthy. These checks perform no physical print or scan.

## Importing saved labels

After the first start, import only saved rich-text editor labels from the former
ai-label-printer installation:

    python3 scripts/import-labels.py

The script ignores AI labels, skips duplicates, and creates a timestamped backup
of the target database before writing.

## Persistence and restarts

Persistent paths are data/cups, data/spool, data/jobs, data/labels, the selected scan directory, and a tiny scanner state directory. OCR has no persistent volume.

Every service uses restart: unless-stopped. Docker restarts them after a process failure and after a host reboot unless an administrator explicitly stopped them.

## Updates

    git pull --ff-only
    docker compose up -d --build
    make validate

Back up labels and scans before major upgrades.
