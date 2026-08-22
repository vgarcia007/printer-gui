# Architecture and security

    Browser :8081
          |
         web ---- CUPS protocol ---- cups ---- LAN/USB printers
          |                           |
          |                       persistent queue state
          |
          +---- scan control ---- scanner ---- Brother device
          |                          |
          |                     2 GiB temporary RAM
          |                          |
          +---- scan files <---- OCR request ---- ocr
                 NAS/shared dir                 2 GiB temporary RAM

Only web publishes a port. CUPS, scanner, and OCR communicate on the private Compose network.

## Data lifecycle

Print uploads are atomically stored in data/jobs and removed only after CUPS accepts them. Saved labels live in SQLite under data/labels.

Scanner pages and intermediate PDFs remain in the scanner's bounded /work tmpfs. OCR receives one final assembled PDF and creates a per-request temporary directory in its own bounded /work tmpfs. The OCR container is read-only, has no persistent work volume, and always removes the request directory.

The final searchable PDF is written through a hidden partial file followed by an atomic rename. Partials older than 24 hours are removed at scanner startup. If OCR fails, only the raw rescue PDF is retained and the interface offers a retry.

## Trust model

There is no authentication. The deployment is safe only on a trusted LAN. User-controlled file names are constrained to configured directories, symlinks are rejected, printer configuration is read-only, and only CUPS can access the DYMO USB device.
