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

## HTTPS reverse proxy and PWA installation

PWA installation requires a secure HTTPS origin. An anonymized Apache example is
available at `deploy/apache-vhost.example.conf`. It intentionally contains no
real domain, certificate path, account, or private network information.

1. Copy the example outside the repository to
   `/etc/apache2/sites-available/print-scan-hub.conf`.
2. Replace every value in angle brackets. `LOCAL_APP_PORT` is `8081` with the
   default Compose configuration.
3. Limit access to your trusted network, or configure authentication or a VPN.
   The application itself has no user accounts.
4. Enable the required modules and site, test the configuration, then reload:

       sudo a2enmod headers proxy proxy_http ssl
       sudo a2ensite print-scan-hub.conf
       sudo apache2ctl configtest
       sudo systemctl reload apache2

5. Open the HTTPS address in a supported browser and select **Install app** or
   **Add to Home Screen**. Printing and scanning still require a live connection
   to the server; only the static offline explanation is cached.

Do not commit the completed host configuration. Certificate private keys,
authentication files, private addresses, and deployment-specific hostnames must
remain outside the repository.

## Importing saved labels

After the first start, import only saved rich-text editor labels from the former
ai-label-printer installation:

    python3 scripts/import-labels.py

The script ignores AI labels, skips duplicates, and creates a timestamped backup
of the target database before writing.

## Persistence and restarts

Persistent paths are data/cups, data/spool, data/jobs, data/labels, the selected scan directory, and a tiny scanner state directory. OCR has no persistent volume.

`data/jobs`, or the path selected with `JOBS_HOST_DIR`, is an automatic print
hotfolder. Share that host directory over the trusted LAN if required. Copying
a complete PDF into it sends the file to `defaultDocumentPrinter`; the web
service waits for a stable file and a valid PDF end marker before submission.

Every service uses restart: unless-stopped. Docker restarts them after a process failure and after a host reboot unless an administrator explicitly stopped them.

## Updates

    git pull --ff-only
    docker compose up -d --build
    make validate

Back up labels and scans before major upgrades.
