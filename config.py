import os
from pathlib import Path


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "development-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:////data/labels/labels.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Strict"
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024
    EDITOR_CONTENT_MAX_LENGTH = 6_000_000
    LABEL_TEMPLATE_DIR = Path(
        os.environ.get("LABEL_TEMPLATE_DIR", "/app/label_templates")
    )
    LABEL_IMAGE_DPI = 300
    IMAGE_MAX_PIXELS = 20_000_000
    DYMO_PRINTER_NAME = os.environ.get(
        "DYMO_PRINTER_NAME", "DYMO_LabelWriter_450"
    )
    DYMO_LANDSCAPE_OFFSET_MM = float(
        os.environ.get("DYMO_LANDSCAPE_OFFSET_MM", "0")
    )
    DYMO_LANDSCAPE_SHRINK_MM = float(
        os.environ.get("DYMO_LANDSCAPE_SHRINK_MM", "0")
    )
    DYMO_LANDSCAPE_START_TRIM_MM = float(
        os.environ.get("DYMO_LANDSCAPE_START_TRIM_MM", "0")
    )
    PRINT_TIMEOUT_SECONDS = int(os.environ.get("PRINT_TIMEOUT_SECONDS", "60"))
    MAX_COPIES = int(os.environ.get("MAX_COPIES", "100"))
    CUPS_SERVER = os.environ.get("CUPS_SERVER", "cups:631")
    PRINTER_CONFIG = Path(
        os.environ.get("PRINTER_CONFIG", "/config/printers.json")
    )
    JOBS_DIR = Path(os.environ.get("JOBS_DIR", "/data/jobs"))
    SCANS_DIR = Path(os.environ.get("SCANS_DIR", "/data/scans"))
    SCANNER_URL = os.environ.get("SCANNER_URL", "http://scanner:8080")
    SCANNER_TIMEOUT_SECONDS = int(
        os.environ.get("SCANNER_TIMEOUT_SECONDS", "10")
    )
    WEB_HOST = os.environ.get("WEB_HOST", "0.0.0.0")
    WEB_PORT = int(os.environ.get("WEB_PORT", "8080"))
