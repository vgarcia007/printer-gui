#!/usr/bin/env python3
"""Local-network PDF printing API backed by a remote CUPS server."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import signal
import subprocess
import threading
import uuid
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import parse_qs, urlparse


DEFAULT_CONFIG = Path(os.environ.get("PRINTER_CONFIG", "/config/printers.json"))
DEFAULT_JOBS_DIR = Path(os.environ.get("JOBS_DIR", "/data/jobs"))
DEFAULT_WEB_DIR = Path(os.environ.get("WEB_DIR", "/app/static"))
DEFAULT_CUPS_SERVER = os.environ.get("CUPS_SERVER", "cups:631")
MAX_PDF_SIZE = 100 * 1024 * 1024
PRINTER_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
OPTION_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
SAFE_STEM = re.compile(r"[^A-Za-z0-9ÄÖÜäöüß ._()-]")
URI_SCHEMES = {"http", "https", "ipp", "ipps", "lpd", "socket"}


class PrintError(RuntimeError):
    """A user-facing printing or configuration error."""


class CommandRunner(Protocol):
    def run(
        self, args: list[str], *, timeout: int = 30, check: bool = True
    ) -> subprocess.CompletedProcess[str]: ...


class SubprocessRunner:
    def run(
        self, args: list[str], *, timeout: int = 30, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                args,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError as exc:
            raise PrintError(f"Required command is unavailable: {args[0]}") from exc
        except subprocess.TimeoutExpired as exc:
            raise PrintError("Der Druckdienst antwortet nicht rechtzeitig.") from exc

        if check and result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise PrintError(detail or "Der Druckdienst hat den Auftrag abgelehnt.")
        return result


@dataclass(frozen=True)
class PrinterDefinition:
    name: str
    label: str
    uri: str
    driver: str
    options: dict[str, str]


@dataclass(frozen=True)
class PrinterConfig:
    default_printer: str
    printers: tuple[PrinterDefinition, ...]

    @classmethod
    def load(cls, path: Path) -> "PrinterConfig":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise PrintError(f"Printer configuration not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise PrintError(f"Invalid printer configuration: {exc}") from exc

        if not isinstance(raw, dict) or raw.get("version") != 1:
            raise PrintError("Printer configuration must use schema version 1.")
        items = raw.get("printers")
        if not isinstance(items, list) or not items:
            raise PrintError("At least one printer must be configured.")

        printers: list[PrinterDefinition] = []
        names: set[str] = set()
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise PrintError(f"Printer entry {index + 1} must be an object.")
            name = item.get("name")
            label = item.get("label")
            uri = item.get("uri")
            driver = item.get("driver")
            options = item.get("options", {})
            if not isinstance(name, str) or not PRINTER_NAME.fullmatch(name):
                raise PrintError(f"Invalid printer name in entry {index + 1}.")
            if name in names:
                raise PrintError(f"Duplicate printer name: {name}")
            if not isinstance(label, str) or not label.strip():
                raise PrintError(f"Printer {name} needs a label.")
            if not isinstance(uri, str) or urlparse(uri).scheme not in URI_SCHEMES:
                raise PrintError(f"Printer {name} has an unsupported URI.")
            if not isinstance(driver, str) or not driver.strip():
                raise PrintError(f"Printer {name} needs a CUPS driver.")
            if not isinstance(options, dict):
                raise PrintError(f"Printer {name} options must be an object.")
            normalized_options: dict[str, str] = {}
            for key, value in options.items():
                if not isinstance(key, str) or not OPTION_NAME.fullmatch(key):
                    raise PrintError(f"Printer {name} has an invalid option name.")
                if not isinstance(value, (str, int, float, bool)):
                    raise PrintError(f"Printer {name} option {key} must be a scalar value.")
                normalized_options[key] = str(value)
            names.add(name)
            printers.append(
                PrinterDefinition(name, label.strip(), uri, driver, normalized_options)
            )

        default = raw.get("defaultPrinter")
        if not isinstance(default, str) or default not in names:
            raise PrintError("defaultPrinter must reference a configured printer.")
        return cls(default, tuple(printers))

    def by_name(self) -> dict[str, PrinterDefinition]:
        return {printer.name: printer for printer in self.printers}


class PrintService:
    def __init__(
        self,
        jobs_dir: Path,
        config_path: Path,
        cups_server: str,
        runner: CommandRunner | None = None,
    ) -> None:
        self.jobs_dir = jobs_dir.resolve()
        self.config_path = config_path
        self.cups_server = cups_server
        self.runner = runner or SubprocessRunner()
        self.lock = threading.RLock()
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    def config(self) -> PrinterConfig:
        return PrinterConfig.load(self.config_path)

    def _cups(self, *args: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
        return self.runner.run([*args], timeout=timeout, check=True)

    def printers(self) -> tuple[list[dict[str, object]], str]:
        config = self.config()
        result = self._cups("lpstat", "-h", self.cups_server, "-p", "-d")
        configured = config.by_name()
        printers: list[dict[str, object]] = []

        for line in result.stdout.splitlines():
            if not line.startswith("printer "):
                continue
            parts = line.split()
            if len(parts) < 3 or parts[1] not in configured:
                continue
            definition = configured[parts[1]]
            ready = " disabled " not in f" {line} " and (
                " is idle." in line or " now printing " in line
            )
            printers.append(
                {"name": definition.name, "label": definition.label, "ready": ready}
            )

        order = {printer.name: index for index, printer in enumerate(config.printers)}
        printers.sort(key=lambda item: order[str(item["name"])])
        return printers, config.default_printer

    def pdf_jobs(self) -> list[Path]:
        return sorted(
            (
                path
                for path in self.jobs_dir.iterdir()
                if path.is_file()
                and not path.is_symlink()
                and path.suffix.lower() == ".pdf"
            ),
            key=lambda path: path.name.lower(),
        )

    def status(self) -> dict[str, object]:
        printers, default = self.printers()
        jobs = self.pdf_jobs()
        return {
            "printers": printers,
            "defaultPrinter": default,
            "jobCount": len(jobs),
            "jobs": [path.name for path in jobs],
        }

    def _validate_printer(self, printer: str) -> None:
        if not PRINTER_NAME.fullmatch(printer):
            raise PrintError("Ungültige Druckerauswahl.")
        config = self.config()
        if printer not in config.by_name():
            raise PrintError("Der gewählte Drucker ist nicht konfiguriert.")
        available, _ = self.printers()
        if printer not in {str(item["name"]) for item in available}:
            raise PrintError("Der gewählte Drucker ist in CUPS nicht verfügbar.")

    def print_files(self, printer: str, files: list[Path]) -> int:
        if not files:
            raise PrintError("Es sind keine PDF-Dateien zum Drucken vorhanden.")

        with self.lock:
            self._validate_printer(printer)
            printed = 0
            for path in files:
                try:
                    resolved = path.resolve(strict=True)
                except FileNotFoundError:
                    continue
                if (
                    resolved.parent != self.jobs_dir
                    or path.is_symlink()
                    or resolved.suffix.lower() != ".pdf"
                ):
                    continue
                self._cups(
                    "lpr",
                    "-H",
                    self.cups_server,
                    "-P",
                    printer,
                    str(resolved),
                    timeout=60,
                )
                resolved.unlink()
                printed += 1
            if not printed:
                raise PrintError("Es sind keine PDF-Dateien zum Drucken vorhanden.")
            return printed

    def save_upload(self, filename: str, content: bytes) -> Path:
        clean_name = Path(filename).name.strip()
        if not clean_name.lower().endswith(".pdf"):
            raise PrintError("Bitte wähle eine PDF-Datei aus.")
        if not content or b"%PDF-" not in content[:1024]:
            raise PrintError("Die ausgewählte Datei ist keine gültige PDF.")

        stem = SAFE_STEM.sub("_", Path(clean_name).stem).strip() or "Dokument"
        candidate = self.jobs_dir / f"{stem}.pdf"
        counter = 2
        while candidate.exists():
            candidate = self.jobs_dir / f"{stem} ({counter}).pdf"
            counter += 1

        temporary = self.jobs_dir / f".upload-{uuid.uuid4().hex}.tmp"
        try:
            with temporary.open("xb") as stream:
                stream.write(content)
            os.replace(temporary, candidate)
        finally:
            if temporary.exists():
                temporary.unlink()
        return candidate


class PrinterHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def make_handler(service: PrintService, web_dir: Path) -> type[BaseHTTPRequestHandler]:
    static_root = web_dir.resolve()

    class Handler(BaseHTTPRequestHandler):
        server_version = "PrinterGUI/1.0"

        def log_message(self, fmt: str, *args: object) -> None:
            print(f"[{self.log_date_time_string()}] {fmt % args}", flush=True)

        def _security_headers(self) -> None:
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; style-src 'self' 'unsafe-inline'; "
                "script-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                "frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            )

        def _json(
            self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK
        ) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self._security_headers()
            self.end_headers()
            self.wfile.write(body)

        def _error(self, exc: Exception) -> None:
            message = str(exc).strip() or "Unbekannter Fehler"
            self._json({"ok": False, "error": message}, HTTPStatus.BAD_REQUEST)

        def _same_origin(self) -> bool:
            origin = self.headers.get("Origin")
            if not origin:
                return True
            parsed = urlparse(origin)
            return parsed.scheme in {"http", "https"} and parsed.netloc == self.headers.get("Host")

        def _serve_file(self, path: Path) -> None:
            try:
                resolved = path.resolve(strict=True)
            except FileNotFoundError:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            if resolved != static_root and static_root not in resolved.parents:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            content = resolved.read_bytes()
            mime = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
            self.send_response(HTTPStatus.OK)
            self.send_header(
                "Content-Type", f"{mime}; charset=utf-8" if mime.startswith("text/") else mime
            )
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self._security_headers()
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self) -> None:  # noqa: N802
            request = urlparse(self.path)
            if request.path == "/health":
                self._json({"ok": True})
                return
            if request.path == "/api/status":
                try:
                    self._json({"ok": True, **service.status()})
                except Exception as exc:
                    self._error(exc)
                return
            relative = "index.html" if request.path == "/" else request.path.lstrip("/")
            self._serve_file(static_root / relative)

        def do_POST(self) -> None:  # noqa: N802
            if not self._same_origin():
                self._json(
                    {"ok": False, "error": "Cross-origin requests are not allowed."},
                    HTTPStatus.FORBIDDEN,
                )
                return

            request = urlparse(self.path)
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 0 or length > MAX_PDF_SIZE:
                    raise PrintError("Die PDF darf höchstens 100 MB groß sein.")

                if request.path == "/api/print-jobs":
                    data = json.loads(self.rfile.read(length) or b"{}")
                    count = service.print_files(
                        str(data.get("printer", "")), service.pdf_jobs()
                    )
                elif request.path == "/api/print-pdf":
                    query = parse_qs(request.query)
                    printer = query.get("printer", [""])[0]
                    filename = query.get("filename", ["Dokument.pdf"])[0]
                    path = service.save_upload(filename, self.rfile.read(length))
                    try:
                        count = service.print_files(printer, [path])
                    except Exception as exc:
                        raise PrintError(f"{exc} Die PDF bleibt im Jobs-Ordner.") from exc
                else:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._json({"ok": True, "printed": count})
            except Exception as exc:
                self._error(exc)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="LAN web interface for CUPS printing")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--jobs-dir", type=Path, default=DEFAULT_JOBS_DIR)
    parser.add_argument("--web-dir", type=Path, default=DEFAULT_WEB_DIR)
    parser.add_argument("--cups-server", default=DEFAULT_CUPS_SERVER)
    args = parser.parse_args()

    service = PrintService(args.jobs_dir, args.config, args.cups_server)
    service.config()
    server = PrinterHTTPServer((args.host, args.port), make_handler(service, args.web_dir))
    print(f"Printer GUI listening on http://{args.host}:{args.port}", flush=True)

    def stop_server(_signum: int, _frame: Any) -> None:
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop_server)
    signal.signal(signal.SIGINT, stop_server)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
