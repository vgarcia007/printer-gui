from __future__ import annotations

import mimetypes
import os
import re
from datetime import datetime
from pathlib import Path


SAFE_NAME = re.compile(r"^[A-Za-z0-9ÄÖÜäöüßÀ-ÿ ._()&+,'-]{3,200}$")


class ScanFileError(RuntimeError):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


class ScanFileService:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, filename: str) -> Path:
        if Path(filename).name != filename or not filename.lower().endswith(".pdf"):
            raise ScanFileError("The file name is invalid.")
        path = self.root / filename
        try:
            resolved = path.resolve(strict=True)
        except FileNotFoundError as exc:
            raise ScanFileError("The scan no longer exists.", 404) from exc
        if resolved.parent != self.root or path.is_symlink() or not resolved.is_file():
            raise ScanFileError("The scan cannot be accessed.")
        if mimetypes.guess_type(resolved.name)[0] != "application/pdf":
            raise ScanFileError("Only PDF scans can be accessed.")
        return resolved

    def list(self) -> list[dict[str, object]]:
        items = []
        for path in self.root.iterdir():
            if not path.is_file() or path.is_symlink() or path.suffix.lower() != ".pdf":
                continue
            stat = path.stat()
            items.append(
                {
                    "filename": path.name,
                    "name": path.stem,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "ocrFailed": path.stem.endswith("-ocr-failed"),
                }
            )
        return sorted(items, key=lambda item: str(item["modified"]), reverse=True)

    def rename(self, filename: str, name: str, prefix: str) -> str:
        source = self.resolve(filename)
        name = name.strip()
        if not SAFE_NAME.fullmatch(name) or name.lower().endswith(".pdf"):
            raise ScanFileError("Enter a name between 3 and 200 safe characters without .pdf.")
        if prefix not in {"none", "date", "datetime"}:
            raise ScanFileError("The selected prefix is invalid.")
        stamp = datetime.fromtimestamp(source.stat().st_mtime)
        lead = ""
        if prefix == "date":
            lead = stamp.strftime("%Y-%m-%d ")
        elif prefix == "datetime":
            lead = stamp.strftime("%Y-%m-%d-%H-%M-%S ")
        destination = self.root / f"{lead}{name}.pdf"
        if destination.exists() and destination != source:
            raise ScanFileError("A scan with that name already exists.", 409)
        times = (source.stat().st_atime, source.stat().st_mtime)
        os.replace(source, destination)
        os.utime(destination, times)
        return destination.name

    def delete(self, filename: str) -> None:
        self.resolve(filename).unlink()

