# Architecture and security

## Components

```text
Browser ──HTTP:8080──> web ──CUPS:631──> cups ──LAN──> printers
                         │                   │
                    data/jobs          data/cups
                                        data/spool
```

The `web` container serves one static page and a small Python standard-library API. It submits files with the CUPS command-line client. The `cups` container owns printer drivers, queues, conversion filters, and spool state. Only the web port is published.

## Print flows

For **print all jobs**, the service lists regular `.pdf` files directly inside `data/jobs`, submits them one by one, and deletes each file after CUPS accepts it.

For an uploaded PDF, the service checks the extension, size, and PDF signature, writes it atomically into `data/jobs`, and submits it. If submission fails, the file is retained.

The API serializes print operations to avoid overlapping deletion or duplicate submissions. It rejects symlinks and paths outside the jobs directory.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Container liveness check |
| `GET` | `/api/status` | Printers, readiness, default, and queued PDF names |
| `POST` | `/api/print-jobs` | Print all PDFs in `data/jobs` |
| `POST` | `/api/print-pdf?printer=...&filename=...` | Upload and print one PDF |

The upload limit is 100 MB. POST requests with a foreign `Origin` header are rejected. Browser security headers prevent framing and restrict resource loading.

## Security model

There are no accounts, sessions, or authorization rules. This is a deliberate appliance-style design for a trusted household network. Network access to port 8080 is equivalent to permission to print.

The web container runs as an unprivileged user. It has no Docker socket and cannot administer queues. Printer configuration is mounted read-only into both services. The CUPS service is not published to the host network.
