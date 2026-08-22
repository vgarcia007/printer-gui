# Debian validation handoff

This document records the implementation state on 22 August 2026 and the exact work to continue in a Codex session on the target Debian Docker host.

## Current state

The repository has been rebuilt from the former Steam Deck/Podman project into a self-contained Docker Compose application.

Completed:

- A responsive single-screen German web UI for printing all files in `data/jobs` or one selected/dropped PDF
- A Python standard-library web API with no accounts or external runtime packages
- Two declarative queues in `config/printers.json`
- `hp-color` set as the CUPS and dropdown default
- Brother MFC-L2710DW configured with `brlaser`
- HP Color Laser MFP 178nw configured with the HP 17x SPL-C PPD and raster filter
- Separate `web` and `cups` container images
- Repository-local persistent directories for jobs, CUPS state, and spool data
- English installation, configuration, architecture, troubleshooting, and development documentation
- Unit coverage for configuration, status, upload validation, path safety, deletion behavior, HTTP health/status, and same-origin rejection

Validation already completed on the development host:

- 9 Python tests pass
- Python bytecode compilation passes
- Both shell entrypoints pass `sh -n`
- `config/printers.json` parses successfully
- `git diff --check` passes

Not completed on the development host:

- Docker Compose schema rendering
- Container image builds
- Live startup and health checks
- Inspection of driver options from the installed HP PPD

The reason is environmental: the development host has no `docker` executable. A fallback Podman build was intentionally stopped when the work was handed over. No real print job has been submitted.

## Continue on the Debian host

Start in the cloned repository and let the next Codex session read this document, `README.md`, and `docs/configuration.md` before changing files.

### 1. Inspect the host and repository

```bash
git status --short
docker version
docker compose version
ip route
```

Confirm that the working tree is clean and that Docker Compose v2 is available.

### 2. Confirm printer addresses

The current known addresses are:

```text
Brother MFC-L2710DW:       192.168.188.133
HP Color Laser MFP 178nw: 192.168.188.71
```

Check reachability without printing:

```bash
ping -c 2 192.168.188.133
ping -c 2 192.168.188.71
```

If the target Debian server is on another subnet or DHCP changed an address, update only the corresponding `uri` in `config/printers.json`. Prefer DHCP reservations in the router.

### 3. Run static validation

```bash
make validate
```

This includes `docker compose config --quiet` and does not submit print jobs.

### 4. Build both images

```bash
docker compose build --pull
```

Pay particular attention to the `cups` build. It must:

- download the HP ULD archive successfully;
- match SHA-256 `cebb9b7b6125e7406634bb9c2a98b01477d1e11d66c7c90474669de9927bc91d`;
- select `x86_64` for Docker `amd64` or `aarch64` for Docker `arm64`;
- pass `cupstestppd`;
- show no unresolved required library in `ldd /usr/lib/cups/filter/rastertospl`.

If HP removes or replaces the download, do not silently disable checksum validation. Find the official replacement, verify it independently, and update both the URL and checksum with documentation.

### 5. Start and inspect without printing

```bash
docker compose up -d
docker compose ps
docker compose logs --tail=200 cups
docker compose logs --tail=100 web
curl --fail http://localhost:8080/health
curl --fail http://localhost:8080/api/status
```

Expected API facts:

- two printers are returned;
- their names are `mfc` and `hp-color`;
- `defaultPrinter` is `hp-color`;
- both containers become healthy.

Inspect CUPS and filters:

```bash
docker compose exec cups lpstat -p -d
docker compose exec cups lpstat -v
docker compose exec cups lpinfo -m | grep -E 'brl2710w|HP_Color_Laser_MFP_17x'
docker compose exec cups test -x /usr/lib/cups/filter/rastertospl
docker compose exec cups ldd /usr/lib/cups/filter/rastertospl
docker compose exec cups lpoptions -p hp-color -l
```

The default must be `hp-color`. Confirm that the configured option keys in `config/printers.json` exist in `lpoptions -p hp-color -l`. If the HP PPD uses different color or quality keys, replace only the invalid defaults and document the discovered values.

### 6. Browser smoke test

Open `http://DEBIAN-SERVER-IP:8080` from another household device.

Confirm without pressing a print button:

- the page loads cleanly on desktop and mobile widths;
- the status shows the service as ready;
- both printers appear;
- HP Color Laser MFP 178nw is initially selected;
- drag and drop highlights the drop area;
- files already placed in `data/jobs` are counted after refresh.

### 7. Controlled physical print test

Only after all non-printing checks pass, create or select a one-page PDF containing a distinctive short line and test one printer at a time. Keep physical access to the HP printer so its queue can be cancelled immediately if output is wrong.

For the HP test, watch the CUPS log while submitting:

```bash
docker compose logs -f cups
```

Success criteria:

- exactly one page is produced;
- text and color render normally;
- CUPS logs show the raster/SPL-C filter path rather than raw passthrough;
- the source PDF disappears from `data/jobs` only after CUPS accepts it.

Then repeat with the Brother queue.

### 8. Final repository update

If Debian-specific fixes are required:

```bash
make validate
git diff --check
git status --short
git add -A
git commit -m "Validate Docker deployment on Debian"
git push
```

Document any changed printer address, driver option, base-image compatibility fix, or operational caveat in the appropriate English Markdown file.

## Constraints to preserve

- Do not add user accounts; the application is intended for a trusted private LAN.
- Do not publish CUPS port 631 from Compose.
- Do not mount the Docker socket into the web container.
- Do not use `raw`, generic PostScript, or `everywhere` for the HP 178nw unless a controlled test proves the exact device supports it; the current solution intentionally converts to SPL-C.
- Do not delete PDFs before a successful CUPS submission.
- Keep configuration and persistent data below the repository directory.
- Keep all project documentation in English.
- Do not run automated tests that submit physical print jobs.
