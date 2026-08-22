# Troubleshooting

Start with:

    docker compose ps
    docker compose logs --tail=100 web cups scanner ocr

## The page is unavailable

Port 8081 must be free and reachable from the LAN. Check .env, then run docker compose up -d.

## A printer is unavailable

Check config/printers.local.json, then inspect queues with docker compose exec cups lpstat -p -d. The HP queue must retain the HP 17x SPL-C driver; a raw or generic PostScript queue can produce garbage pages.

For DYMO problems, confirm the USB device is visible with docker compose exec cups lsusb and that its URI is correct.

## The scanner is unavailable

Check SCANNER_IP, then run:

    docker compose exec scanner brsaneconfig4 -q
    docker compose exec scanner scanimage -L

Do not run an actual scanimage command unless paper is loaded and a physical scan is intended.

## OCR fails

Inspect scanner and OCR logs. The rescue PDF remains in the scan directory with -ocr-failed in its name and can be downloaded or retried.

OCR scratch data cannot grow persistently: it exists only in a 2 GiB tmpfs and per-job directories are deleted. Restarting OCR clears the complete work area.

## A PDF remains in the print jobs folder

This is intentional after a failed CUPS submission. Correct the printer problem and submit it again.
