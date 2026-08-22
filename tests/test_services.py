from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.services.document_service import (
    DocumentPrintError,
    DocumentPrintService,
    PrinterConfig,
)
from app.services.scan_file_service import ScanFileError, ScanFileService


CONFIG = {
    "version": 2,
    "defaultDocumentPrinter": "hp-color",
    "labelPrinter": "DYMO_LabelWriter_450",
    "printers": [
        {
            "name": "mfc",
            "label": "Brother MFC-L2710DW",
            "kind": "document",
            "uri": "ipp://192.0.2.30/ipp/print",
            "driver": "brother.ppd",
            "options": {"PageSize": "A4"},
        },
        {
            "name": "hp-color",
            "label": "HP Color Laser MFP 178nw",
            "kind": "document",
            "uri": "socket://192.0.2.31",
            "driver": "hp.ppd",
            "options": {"PageSize": "A4"},
        },
        {
            "name": "DYMO_LabelWriter_450",
            "label": "DYMO LabelWriter 450",
            "kind": "label",
            "uri": "usb://DYMO/LabelWriter%20450",
            "driver": "dymo.ppd",
            "options": {},
        },
    ],
}


def completed(args, output=""):
    return subprocess.CompletedProcess(args, 0, output, "")


class DocumentServiceTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.jobs = self.root / "jobs"
        self.config_path = self.root / "printers.json"
        self.config_path.write_text(json.dumps(CONFIG), encoding="utf-8")
        self.service = DocumentPrintService(self.jobs, self.config_path, "cups:631")

    def tearDown(self):
        self.temporary.cleanup()

    def lpstat(self, args, **_kwargs):
        if args[0] == "lpstat":
            return completed(
                args,
                "printer mfc is idle. enabled since now\n"
                "printer hp-color is idle. enabled since now\n"
                "printer DYMO_LabelWriter_450 is idle. enabled since now\n",
            )
        return completed(args)

    def test_schema_separates_document_and_label_printers(self):
        config = PrinterConfig.load(self.config_path)
        self.assertEqual(config.default_document_printer, "hp-color")
        self.assertEqual(config.label_printer, "DYMO_LabelWriter_450")
        self.assertEqual([item.kind for item in config.printers], ["document", "document", "label"])

    @patch("app.services.document_service.subprocess.run")
    def test_status_excludes_label_printer(self, run):
        run.side_effect = self.lpstat
        (self.jobs / "A.pdf").write_bytes(b"%PDF-1.7\n")
        (self.jobs / "ignore.txt").write_text("no", encoding="utf-8")
        status = self.service.status()
        self.assertEqual([item["name"] for item in status["printers"]], ["mfc", "hp-color"])
        self.assertEqual(status["jobs"], ["A.pdf"])

    def test_upload_is_validated_and_sanitized(self):
        path = self.service.save_upload("../invoice<script>.PDF", b"%PDF-1.7\nbody")
        self.assertEqual(path.name, "invoice_script_.pdf")
        with self.assertRaisesRegex(DocumentPrintError, "valid PDF"):
            self.service.save_upload("notes.pdf", b"plain text")

    @patch("app.services.document_service.subprocess.run")
    def test_file_is_removed_only_after_cups_accepts_it(self, run):
        run.side_effect = self.lpstat
        path = self.jobs / "document.pdf"
        path.write_bytes(b"%PDF-1.7\n")
        self.assertEqual(self.service.print_files("hp-color", [path]), 1)
        self.assertFalse(path.exists())

        failed = self.jobs / "failed.pdf"
        failed.write_bytes(b"%PDF-1.7\n")
        calls = 0

        def reject(args, **_kwargs):
            nonlocal calls
            calls += 1
            if args[0] == "lpr":
                return subprocess.CompletedProcess(args, 1, "", "printer unavailable")
            return self.lpstat(args)

        run.side_effect = reject
        with self.assertRaises(DocumentPrintError):
            self.service.print_files("hp-color", [failed])
        self.assertTrue(failed.exists())


class ScanFileServiceTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.service = ScanFileService(self.root)

    def tearDown(self):
        self.temporary.cleanup()

    def test_list_rename_and_delete(self):
        source = self.root / "2026-08-22-12-30-00.pdf"
        source.write_bytes(b"%PDF-1.7\n")
        self.assertEqual(len(self.service.list()), 1)
        renamed = self.service.rename(source.name, "Electricity bill", "date")
        self.assertEqual(renamed, "2026-08-22 Electricity bill.pdf")
        self.service.delete(renamed)
        self.assertEqual(self.service.list(), [])

    def test_paths_cannot_escape_scan_directory(self):
        outside = self.root.parent / "secret.pdf"
        outside.write_bytes(b"%PDF-1.7\n")
        self.addCleanup(outside.unlink)
        with self.assertRaises(ScanFileError):
            self.service.resolve("../secret.pdf")


class PageSmokeTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        printer_config = root / "printers.json"
        printer_config.write_text(json.dumps(CONFIG), encoding="utf-8")

        class Overrides:
            TESTING = True
            WTF_CSRF_ENABLED = False
            SECRET_KEY = "test"
            SQLALCHEMY_DATABASE_URI = "sqlite:///" + str(root / "labels.db")
            JOBS_DIR = root / "jobs"
            SCANS_DIR = root / "scans"
            PRINTER_CONFIG = printer_config
            LABEL_TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "label_templates"

        self.app = create_app(Overrides)
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.temporary.cleanup()

    def test_main_pages_are_english_and_have_security_headers(self):
        for path in ("/", "/documents", "/labels", "/labels/gallery", "/scans", "/scans/files"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn(b"Print & Scan Hub", response.data)
            self.assertEqual(response.headers["X-Frame-Options"], "DENY")
            self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])


if __name__ == "__main__":
    unittest.main()
