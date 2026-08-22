from __future__ import annotations

import logging
from io import BytesIO
import math
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image, UnidentifiedImageError
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


logger = logging.getLogger(__name__)


class PrintError(RuntimeError):
    """A user-safe printing error."""


class CupsUnavailableError(PrintError):
    pass


class PrinterNotFoundError(PrintError):
    pass


class PrinterOfflineError(PrintError):
    pass


class PdfConversionError(PrintError):
    pass


class InvalidCopiesError(PrintError):
    pass


@dataclass(frozen=True)
class PrinterStatus:
    state: str
    message: str


class LabelPrintService:
    PRINTER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,126}$")

    def __init__(
        self,
        printer_name: str,
        cups_server: str = "cups:631",
        timeout_seconds: int = 30,
        max_copies: int = 100,
        landscape_offset_mm: float = 0.0,
        landscape_shrink_mm: float = 0.0,
        landscape_start_trim_mm: float = 0.0,
        runner: Callable = subprocess.run,
    ):
        if not self.PRINTER_RE.fullmatch(printer_name or ""):
            raise ValueError("The configured CUPS printer name is invalid.")
        self.printer_name = printer_name
        self.cups_server = cups_server
        self.timeout_seconds = timeout_seconds
        self.max_copies = max_copies
        self.landscape_offset_mm = float(landscape_offset_mm)
        if (
            not math.isfinite(self.landscape_offset_mm)
            or abs(self.landscape_offset_mm) > 20
        ):
            raise ValueError("The configured DYMO print offset is invalid.")
        self.landscape_shrink_mm = float(landscape_shrink_mm)
        if (
            not math.isfinite(self.landscape_shrink_mm)
            or not 0 <= self.landscape_shrink_mm <= 20
        ):
            raise ValueError("The configured DYMO print shrink value is invalid.")
        self.landscape_start_trim_mm = float(landscape_start_trim_mm)
        if (
            not math.isfinite(self.landscape_start_trim_mm)
            or not 0 <= self.landscape_start_trim_mm <= 20
        ):
            raise ValueError(
                "The configured DYMO leading-edge trim is invalid."
            )
        self.runner = runner

    @staticmethod
    def _environment() -> dict[str, str]:
        environment = os.environ.copy()
        environment["LC_ALL"] = "C"
        environment["LANG"] = "C"
        return environment

    def _run(self, command: list[str]) -> subprocess.CompletedProcess:
        try:
            return self.runner(
                command,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout_seconds,
                check=False,
                shell=False,
                env=self._environment(),
            )
        except FileNotFoundError as exc:
            raise CupsUnavailableError(
                "The CUPS command-line tools are not installed."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise CupsUnavailableError(
                "CUPS did not respond in time."
            ) from exc
        except OSError as exc:
            logger.exception("CUPS command could not be started")
            raise CupsUnavailableError(
                "The connection to the printing system failed."
            ) from exc

    @staticmethod
    def _combined(result: subprocess.CompletedProcess) -> str:
        return f"{result.stdout or ''}\n{result.stderr or ''}".strip()

    @staticmethod
    def _is_scheduler_error(output: str) -> bool:
        lowered = output.lower()
        return any(
            marker in lowered
            for marker in (
                "scheduler is not running",
                "connection refused",
                "failed to connect",
                "server-error-service-unavailable",
            )
        )

    def get_status(self) -> PrinterStatus:
        try:
            result = self._run(
                ["lpstat", "-h", self.cups_server, "-l", "-p", self.printer_name]
            )
        except CupsUnavailableError as exc:
            return PrinterStatus("unknown", str(exc))
        output = self._combined(result)
        lowered = output.lower()
        if result.returncode != 0:
            if self._is_scheduler_error(output):
                return PrinterStatus("unknown", "CUPS is unavailable.")
            if any(
                marker in lowered
                for marker in ("unknown printer", "not found", "no destinations")
            ):
                return PrinterStatus("unknown", "The configured printer does not exist.")
            return PrinterStatus("unknown", "The printer status is unknown.")
        if "disabled" in lowered or "stopped" in lowered:
            return PrinterStatus("stopped", "The printer is stopped.")
        if "offline" in lowered or "not responding" in lowered:
            return PrinterStatus("offline", "The printer is offline.")
        if "is idle" in lowered or "now printing" in lowered or "enabled" in lowered:
            return PrinterStatus("available", "The printer is available.")
        return PrinterStatus("unknown", "The printer status is unknown.")

    def get_options(self) -> str:
        result = self._run(
            ["lpoptions", "-h", self.cups_server, "-p", self.printer_name, "-l"]
        )
        output = self._combined(result)
        if result.returncode != 0:
            if self._is_scheduler_error(output):
                raise CupsUnavailableError("CUPS is unavailable.")
            if "unknown printer" in output.lower() or "not found" in output.lower():
                raise PrinterNotFoundError(
                    "The configured DYMO printer was not found."
                )
            raise PrintError("The printer options could not be read.")
        return result.stdout or ""

    @staticmethod
    def media_name(width_mm: float, height_mm: float) -> str:
        return f"Custom.{width_mm:g}x{height_mm:g}mm"

    def build_print_command(
        self, pdf_path: Path, copies: int, width_mm: float, height_mm: float
    ) -> list[str]:
        self.validate_copies(copies)
        return [
            "lp",
            "-h",
            self.cups_server,
            "-d",
            self.printer_name,
            "-n",
            str(copies),
            "-o",
            f"media={self.media_name(width_mm, height_mm)}",
            "-o",
            "scaling=100",
            "-o",
            "fit-to-page=false",
            str(pdf_path),
        ]

    def validate_copies(self, copies: int) -> None:
        if isinstance(copies, bool) or not isinstance(copies, int):
            raise InvalidCopiesError("The number of copies must be a whole number.")
        if not 1 <= copies <= self.max_copies:
            raise InvalidCopiesError(
                f"The number of copies must be between 1 and {self.max_copies}."
            )

    @staticmethod
    def prepare_png_for_print(
        png_content: bytes,
        width_mm: float,
        height_mm: float,
        landscape_offset_mm: float = 0.0,
        landscape_shrink_mm: float = 0.0,
        landscape_start_trim_mm: float = 0.0,
    ) -> tuple[bytes, float, float]:
        """Apply the established DYMO feed calibration directly to raster data."""
        try:
            with Image.open(BytesIO(png_content)) as source:
                source.load()
                artwork = source.convert("L")
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise PdfConversionError(
                "The PNG could not be prepared for DYMO printing."
            ) from exc

        if width_mm <= height_mm:
            return png_content, width_mm, height_mm

        total_shrink_mm = landscape_shrink_mm + landscape_start_trim_mm
        if (
            landscape_shrink_mm < 0
            or landscape_start_trim_mm < 0
            or not total_shrink_mm < width_mm
        ):
            raise PdfConversionError(
                "The configured DYMO print shrink value is invalid."
            )

        if total_shrink_mm:
            shortened_width = max(
                1,
                round(
                    artwork.width
                    * (width_mm - total_shrink_mm)
                    / width_mm
                ),
            )
            shortened = artwork.resize(
                (shortened_width, artwork.height),
                Image.Resampling.LANCZOS,
            )
            inset_mm = landscape_shrink_mm / 2 + landscape_start_trim_mm
            inset_px = round(artwork.width * inset_mm / width_mm)
            calibrated = Image.new("L", artwork.size, "white")
            calibrated.paste(shortened, (inset_px, 0))
        else:
            calibrated = artwork

        rotated = calibrated.transpose(Image.Transpose.ROTATE_270)
        offset_px = round(rotated.height * landscape_offset_mm / width_mm)
        physical = Image.new("L", rotated.size, "white")
        physical.paste(rotated, (0, offset_px))

        output = BytesIO()
        physical.save(output, format="PNG", optimize=True)
        return output.getvalue(), height_mm, width_mm

    @staticmethod
    def convert_png_to_pdf(
        png_content: bytes,
        pdf_path: Path,
        width_mm: float,
        height_mm: float,
    ) -> None:
        try:
            page_width = width_mm * mm
            page_height = height_mm * mm
            document = canvas.Canvas(
                str(pdf_path),
                pagesize=(page_width, page_height),
                pageCompression=1,
            )
            document.drawImage(
                ImageReader(BytesIO(png_content)),
                0,
                0,
                width=page_width,
                height=page_height,
                preserveAspectRatio=False,
                anchor="c",
            )
            document.showPage()
            document.save()
        except Exception as exc:
            logger.exception("PNG to PDF conversion failed")
            raise PdfConversionError(
                "The label could not be converted to a printable PDF."
            ) from exc
        if not pdf_path.is_file() or pdf_path.stat().st_size == 0:
            raise PdfConversionError("PDF conversion did not create a file.")

    def print_png(
        self,
        png_content: bytes,
        width_mm: float,
        height_mm: float,
        copies: int,
    ) -> str:
        self.validate_copies(copies)
        status = self.get_status()
        if status.state == "offline":
            raise PrinterOfflineError("The DYMO printer is offline.")
        if status.state == "stopped":
            raise PrinterOfflineError("The DYMO printer is stopped.")
        if status.state != "available":
            raise PrintError(status.message)

        printable_png, print_width_mm, print_height_mm = self.prepare_png_for_print(
            png_content,
            width_mm,
            height_mm,
            landscape_offset_mm=self.landscape_offset_mm,
            landscape_shrink_mm=self.landscape_shrink_mm,
            landscape_start_trim_mm=self.landscape_start_trim_mm,
        )
        options = self.get_options()
        media = self.media_name(print_width_mm, print_height_mm)
        if "custom" not in options.lower() and media.lower() not in options.lower():
            logger.warning(
                "CUPS reports no custom media option for %s; trying %s anyway.",
                self.printer_name,
                media,
            )

        with tempfile.TemporaryDirectory(prefix="label-print-") as temp_dir:
            pdf_path = Path(temp_dir) / "label.pdf"
            self.convert_png_to_pdf(
                printable_png,
                pdf_path,
                print_width_mm,
                print_height_mm,
            )
            command = self.build_print_command(
                pdf_path, copies, print_width_mm, print_height_mm
            )
            result = self._run(command)
            output = self._combined(result)
            if result.returncode != 0:
                logger.error("CUPS print job rejected: %.2000s", output)
                if self._is_scheduler_error(output):
                    raise CupsUnavailableError("CUPS is unavailable.")
                if "unknown printer" in output.lower():
                    raise PrinterNotFoundError(
                        "The configured DYMO printer was not found."
                    )
                raise PrintError("CUPS rejected the print job.")
            match = re.search(r"\brequest id is ([^\s]+)", result.stdout or "", re.I)
            return match.group(1) if match else "accepted"
