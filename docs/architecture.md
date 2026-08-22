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

Print uploads are atomically stored in data/jobs and removed only after CUPS
accepts them. The same directory is a print hotfolder: visible PDF files are
submitted to the configured default document printer only after their size and
modification time have remained unchanged for the configured interval, their
header identifies a PDF, and their final bytes contain a PDF end marker. Failed
CUPS submissions remain in place and are retried. Saved labels live in SQLite
under data/labels.

The label editor follows a paper-sheet model: one custom HTML sheet is exactly
88 mm × 34 mm with a 2 mm safe inset and typography expressed in points. The
same sheet is enlarged only for the on-screen editor and rasterized at 300 dpi
into a 1039 × 402 pixel canvas. Content pixels are never resized after that;
the image is only rotated to the DYMO driver's 34 mm × 88 mm feed orientation.

Scanner pages and intermediate PDFs remain in the scanner's bounded /work tmpfs. OCR receives one final assembled PDF and creates a per-request temporary directory in its own bounded /work tmpfs. The OCR container is read-only, has no persistent work volume, and always removes the request directory.

The final searchable PDF is written through a hidden partial file followed by an atomic rename. Partials older than 24 hours are removed at scanner startup. If OCR fails, only the raw rescue PDF is retained and the interface offers a retry.

## Trust model

There is no authentication. The deployment is safe only on a trusted LAN. User-controlled file names are constrained to configured directories, symlinks are rejected, printer configuration is read-only, and only CUPS can access the DYMO USB device.
