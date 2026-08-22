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

Validation completed on the target Debian Docker host:

- Docker 29.6.2 and Docker Compose schema rendering
- Reachability of both configured printer addresses
- `amd64` builds of both images, including the verified HP driver download
- HP PPD validation and runtime library inspection of `rastertospl`
- Live startup and health checks for both containers
- Queue visibility from the web container and API status output
- Inspection of the installed HP PPD options (`A4`, `RGB`, and `Best` are valid)

Two Debian-specific issues were found and resolved:

- Host port 8080 is occupied by UniFi, so this host uses `WEB_PORT=8081` in its ignored `.env` file.
- CUPS queues must use `printer-is-shared=true` so the web container can discover them on the private Compose network. Port 631 remains unpublished.

Not completed:

- Browser smoke test from another household device
- Controlled physical print test on either printer

No real print job has been submitted.

## Continue on the Debian host

Start in the cloned repository and let the next Codex session read this document, `README.md`, and `docs/configuration.md` before changing files.

### 1. Confirm the running deployment

```bash
git status --short
make validate
docker compose ps
curl --fail http://localhost:8081/health
curl --fail http://localhost:8081/api/status
```

Expected facts:

- both containers are healthy;
- two printers are returned;
- their names are `mfc` and `hp-color`;
- `defaultPrinter` is `hp-color`;
- both are reported as ready.

### 2. Browser smoke test

Open `http://192.168.188.117:8081` from another household device.

Confirm without pressing a print button:

- the page loads cleanly on desktop and mobile widths;
- the status shows the service as ready;
- both printers appear;
- HP Color Laser MFP 178nw is initially selected;
- drag and drop highlights the drop area;
- files already placed in `data/jobs` are counted after refresh.

### 3. Controlled physical print test

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

### 4. Final repository update

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
