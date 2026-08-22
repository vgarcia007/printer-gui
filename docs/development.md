# Development

## Layout

- app: Flask interface and print/scan file services
- cups: CUPS image and queue reconciliation
- scanner: Brother SANE scanning and PDF workflow
- ocr: isolated OCRmyPDF API
- config: public printer configuration
- tests: non-printing unit and configuration tests

Run all non-physical checks with:

    make validate

The command compiles Python, validates shell and JSON files, renders Compose, and runs tests in the web image. It never submits a print or scan.

For a live smoke test:

    docker compose up -d --build
    docker compose ps
    curl --fail http://localhost:8081/health

Keep all interface text, errors, comments, tests, and documentation in English. Never add AI generation, scan uploads, messaging credentials, or persistent OCR scratch storage without an explicit project decision.
