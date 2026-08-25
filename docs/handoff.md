# Deployment handoff

Print & Scan Hub replaces the former two-service printer page with four integrated services: web, CUPS, scanner, and OCR.

Before physical acceptance, run make validate and confirm that all four containers are healthy. Then use the browser at port 8081 to perform one controlled test each for a sequential two-PDF queue, a saved DYMO label, a front-only scan, a two-sided scan, and a color scan. For the PDF queue, confirm the displayed order, the current-file progress, the minimum 20-second animation, and the final per-file result before submitting another test.

The old ai-label-printer, BrotherScannerDocker, and OCR service should remain stopped but intact until those tests pass. Revoke the Telegram credential present in the old BrotherScannerDocker configuration; this project does not import or use it.
