# Development

## Repository layout

```text
app/                    Python API and browser interface
config/printers.json    Shared portable printer configuration
cups/                   CUPS image and queue reconciler
data/                   Bind-mounted runtime state
docs/                   Project documentation
tests/                  Python unit and HTTP tests
compose.yaml            Complete deployment definition
```

The runtime application deliberately avoids a package manager: Python's standard library serves the API, while the frontend is plain HTML, CSS, and JavaScript.

## Local checks

```bash
make validate
```

This runs Python unit tests, bytecode compilation, shell syntax checks, JSON parsing, and Compose validation. No real print job is submitted by the tests.

## Container smoke test

```bash
docker compose up -d --build
docker compose ps
curl --fail http://localhost:8080/health
curl --fail http://localhost:8080/api/status
```

Do not call the POST endpoints during a smoke test unless physical printing is intended.

## Design constraints

- Keep deployment self-contained below the repository directory.
- Keep the web service independent of Docker and CUPS administration privileges.
- Treat a successful `lpr` submission as the deletion boundary for a PDF.
- Validate user-controlled filenames and never follow job-directory symlinks.
- Preserve support for both `amd64` and `arm64` when changing the HP driver build.
- Keep all project documentation in English. The end-user interface may remain localized.
