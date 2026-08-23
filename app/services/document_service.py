from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


MAX_PDF_SIZE = 100 * 1024 * 1024
NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
SAFE_STEM = re.compile(r"[^A-Za-z0-9ÄÖÜäöüß ._()-]")
URI_SCHEMES = {"http", "https", "ipp", "ipps", "lpd", "socket", "usb"}


class DocumentPrintError(RuntimeError):
    pass


@dataclass(frozen=True)
class PrinterDefinition:
    name: str
    label: str
    kind: str
    uri: str
    driver: str
    options: dict[str, str]


@dataclass(frozen=True)
class PrinterConfig:
    default_document_printer: str
    label_printer: str
    printers: tuple[PrinterDefinition, ...]

    @classmethod
    def load(cls, path: Path) -> "PrinterConfig":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DocumentPrintError(f"Printer configuration cannot be read: {exc}") from exc
        if raw.get("version") != 2 or not isinstance(raw.get("printers"), list):
            raise DocumentPrintError("Printer configuration must use schema version 2.")
        printers = []
        names = set()
        for item in raw["printers"]:
            name = item.get("name")
            kind = item.get("kind")
            uri = item.get("uri")
            if not isinstance(name, str) or not NAME_RE.fullmatch(name) or name in names:
                raise DocumentPrintError("Printer names must be unique and safe.")
            if kind not in {"document", "label"}:
                raise DocumentPrintError(f"Printer {name} has an invalid kind.")
            if not isinstance(uri, str) or urlparse(uri).scheme not in URI_SCHEMES:
                raise DocumentPrintError(f"Printer {name} has an invalid URI.")
            options = item.get("options", {})
            if not isinstance(options, dict):
                raise DocumentPrintError(f"Printer {name} has invalid options.")
            printers.append(
                PrinterDefinition(
                    name=name,
                    label=str(item.get("label", "")).strip(),
                    kind=kind,
                    uri=uri,
                    driver=str(item.get("driver", "")).strip(),
                    options={str(key): str(value) for key, value in options.items()},
                )
            )
            names.add(name)
        default = raw.get("defaultDocumentPrinter")
        label = raw.get("labelPrinter")
        by_name = {printer.name: printer for printer in printers}
        if default not in by_name or by_name[default].kind != "document":
            raise DocumentPrintError("defaultDocumentPrinter is invalid.")
        if label not in by_name or by_name[label].kind != "label":
            raise DocumentPrintError("labelPrinter is invalid.")
        return cls(default, label, tuple(printers))


class DocumentPrintService:
    def __init__(self, jobs_dir: Path, config_path: Path, cups_server: str):
        self.jobs_dir = Path(jobs_dir).resolve()
        self.config_path = Path(config_path)
        self.cups_server = cups_server
        self.lock = threading.RLock()
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    def config(self) -> PrinterConfig:
        return PrinterConfig.load(self.config_path)

    def _run(self, args: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                args, capture_output=True, text=True, timeout=timeout, check=False
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise DocumentPrintError("The print service did not respond in time.") from exc
        if result.returncode:
            detail = (result.stderr or result.stdout).strip()
            raise DocumentPrintError(detail or "The print service rejected the job.")
        return result

    def printers(self) -> tuple[list[dict[str, object]], str]:
        config = self.config()
        result = self._run(
            ["lpstat", "-h", self.cups_server, "-p", "-d"], timeout=15
        )
        configured = {
            item.name: item for item in config.printers if item.kind == "document"
        }
        available = []
        for line in result.stdout.splitlines():
            if not line.startswith("printer "):
                continue
            parts = line.split()
            if len(parts) < 3 or parts[1] not in configured:
                continue
            item = configured[parts[1]]
            ready = " disabled " not in f" {line} " and (
                " is idle." in line or " now printing " in line
            )
            available.append({"name": item.name, "label": item.label, "ready": ready})
        order = {item.name: index for index, item in enumerate(config.printers)}
        available.sort(key=lambda item: order[str(item["name"])])
        return available, config.default_document_printer

    def pdf_jobs(self) -> list[Path]:
        return sorted(
            (
                path
                for path in self.jobs_dir.iterdir()
                if path.is_file()
                and not path.is_symlink()
                and not path.name.startswith(".")
                and path.suffix.lower() == ".pdf"
            ),
            key=lambda path: path.name.casefold(),
        )

    def status(self) -> dict[str, object]:
        printers, default = self.printers()
        return {
            "printers": printers,
            "defaultPrinter": default,
        }

    def _validate_printer(self, name: str) -> dict[str, object]:
        printers, _ = self.printers()
        for printer in printers:
            if printer["name"] == name:
                return printer
        raise DocumentPrintError("The selected printer is unavailable.")

    def print_files(self, printer: str, files: list[Path]) -> int:
        if not files:
            raise DocumentPrintError("There are no PDF files to print.")
        with self.lock:
            self._validate_printer(printer)
            printed = 0
            for path in files:
                try:
                    resolved = path.resolve(strict=True)
                except FileNotFoundError:
                    continue
                if resolved.parent != self.jobs_dir or path.is_symlink() or resolved.suffix.lower() != ".pdf":
                    continue
                self._run(
                    ["lpr", "-H", self.cups_server, "-P", printer, str(resolved)]
                )
                resolved.unlink()
                printed += 1
            if not printed:
                raise DocumentPrintError("There are no PDF files to print.")
            return printed

    def print_preserved_pdf(self, printer: str, path: Path) -> str:
        with self.lock:
            selected = self._validate_printer(printer)
            try:
                resolved = Path(path).resolve(strict=True)
            except FileNotFoundError as exc:
                raise DocumentPrintError("The PDF no longer exists.") from exc
            if (
                Path(path).is_symlink()
                or not resolved.is_file()
                or resolved.suffix.lower() != ".pdf"
            ):
                raise DocumentPrintError("The selected file is not a printable PDF.")
            try:
                with resolved.open("rb") as stream:
                    header = stream.read(1024)
            except OSError as exc:
                raise DocumentPrintError("The PDF could not be read.") from exc
            if b"%PDF-" not in header:
                raise DocumentPrintError("The selected file is not a valid PDF.")
            self._run(["lpr", "-H", self.cups_server, "-P", printer, str(resolved)])
            return str(selected["label"] or printer)

    def save_upload(self, filename: str, content: bytes) -> Path:
        if len(content) > MAX_PDF_SIZE:
            raise DocumentPrintError("The PDF must not exceed 100 MB.")
        clean = Path(filename).name.strip()
        if not clean.lower().endswith(".pdf") or b"%PDF-" not in content[:1024]:
            raise DocumentPrintError("Please choose a valid PDF file.")
        stem = SAFE_STEM.sub("_", Path(clean).stem).strip() or "Document"
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
            temporary.unlink(missing_ok=True)
        return candidate
