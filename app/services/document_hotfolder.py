from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from .document_service import DocumentPrintError, DocumentPrintService, MAX_PDF_SIZE


@dataclass
class _ObservedFile:
    signature: tuple[int, int]
    stable_since: float
    retry_after: float = 0.0


class DocumentHotfolderService:
    """Print complete PDFs from the jobs directory on the default printer."""

    def __init__(
        self,
        document_service: DocumentPrintService,
        stable_seconds: float = 15.0,
        poll_seconds: float = 2.0,
        retry_seconds: float = 30.0,
        logger: logging.Logger | None = None,
    ):
        if stable_seconds < 1 or poll_seconds <= 0 or retry_seconds <= 0:
            raise ValueError("Hotfolder timing values must be positive.")
        self.document_service = document_service
        self.stable_seconds = stable_seconds
        self.poll_seconds = poll_seconds
        self.retry_seconds = retry_seconds
        self.logger = logger or logging.getLogger(__name__)
        self._observed: dict[Path, _ObservedFile] = {}
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @staticmethod
    def _signature(path: Path) -> tuple[int, int]:
        stat = path.stat(follow_symlinks=False)
        return stat.st_size, stat.st_mtime_ns

    def _is_complete_pdf(
        self, path: Path, expected_signature: tuple[int, int]
    ) -> bool:
        size, _mtime_ns = expected_signature
        if size <= 0 or size > MAX_PDF_SIZE:
            return False
        try:
            with path.open("rb") as stream:
                header = stream.read(min(1024, size))
                stream.seek(max(0, size - 4096))
                trailer = stream.read()
            return (
                b"%PDF-" in header
                and b"%%EOF" in trailer
                and self._signature(path) == expected_signature
            )
        except (FileNotFoundError, OSError):
            return False

    def poll_once(self, now: float | None = None) -> int:
        now = time.monotonic() if now is None else now
        candidates = self.document_service.pdf_jobs()
        candidate_set = set(candidates)
        for vanished in self._observed.keys() - candidate_set:
            self._observed.pop(vanished, None)

        printed = 0
        for path in candidates:
            try:
                signature = self._signature(path)
            except (FileNotFoundError, OSError):
                self._observed.pop(path, None)
                continue

            observation = self._observed.get(path)
            if observation is None or observation.signature != signature:
                self._observed[path] = _ObservedFile(signature, now)
                continue
            if now - observation.stable_since < self.stable_seconds:
                continue
            if now < observation.retry_after:
                continue
            if not self._is_complete_pdf(path, signature):
                observation.retry_after = now + self.retry_seconds
                continue

            try:
                default_printer = (
                    self.document_service.config().default_document_printer
                )
                self.document_service.print_files(default_printer, [path])
            except (DocumentPrintError, OSError) as exc:
                observation.retry_after = now + self.retry_seconds
                self.logger.warning(
                    "Hotfolder could not print %s: %s", path.name, exc
                )
                continue

            self._observed.pop(path, None)
            printed += 1
            self.logger.info(
                "Hotfolder submitted %s to default printer %s",
                path.name,
                default_printer,
            )
        return printed

    def run_forever(self) -> None:
        self.logger.info(
            "PDF hotfolder watching %s (stable for %.0f seconds)",
            self.document_service.jobs_dir,
            self.stable_seconds,
        )
        while not self._stop_event.wait(self.poll_seconds):
            try:
                self.poll_once()
            except Exception:
                self.logger.exception("Unexpected PDF hotfolder error")

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self.run_forever,
            name="pdf-hotfolder",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=max(1.0, self.poll_seconds * 2))
