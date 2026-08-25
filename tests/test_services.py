from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.i18n import normalize_language
from app.services.document_hotfolder import DocumentHotfolderService
from app.services.document_service import (
    DocumentPrintError,
    DocumentPrintService,
    PrinterConfig,
)
from app.services.scan_file_service import ScanFileError, ScanFileService
from app.services.editor_document import sanitize_editor_document


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
        self.assertNotIn("jobs", status)
        self.assertEqual([path.name for path in self.service.pdf_jobs()], ["A.pdf"])

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
            if args[0] == "lp":
                return subprocess.CompletedProcess(args, 1, "", "printer unavailable")
            return self.lpstat(args)

        run.side_effect = reject
        with self.assertRaises(DocumentPrintError):
            self.service.print_files("hp-color", [failed])
        self.assertTrue(failed.exists())

    @patch("app.services.document_service.subprocess.run")
    def test_preserved_pdf_is_printed_without_being_deleted(self, run):
        run.side_effect = self.lpstat
        scans = self.root / "scans"
        scans.mkdir()
        path = scans / "searchable scan.pdf"
        path.write_bytes(b"%PDF-1.7\nsearchable document\n%%EOF\n")

        label = self.service.print_preserved_pdf("mfc", path)

        self.assertTrue(path.exists())
        self.assertEqual(label, "Brother MFC-L2710DW")
        lp_calls = [call.args[0] for call in run.call_args_list if call.args[0][0] == "lp"]
        self.assertEqual(lp_calls, [["lp", "-h", "cups:631", "-d", "mfc", str(path)]])

    @patch("app.services.document_service.subprocess.run")
    def test_hotfolder_waits_for_a_complete_stable_pdf(self, run):
        run.side_effect = self.lpstat
        worker = DocumentHotfolderService(
            self.service,
            stable_seconds=15,
            poll_seconds=1,
            retry_seconds=5,
        )
        path = self.jobs / "network-copy.pdf"
        path.write_bytes(b"%PDF-1.7\npart of the file")

        self.assertEqual(worker.poll_once(now=100), 0)
        self.assertEqual(worker.poll_once(now=115), 0)
        self.assertTrue(path.exists())

        path.write_bytes(b"%PDF-1.7\ncomplete file\n%%EOF\n")
        self.assertEqual(worker.poll_once(now=120), 0)
        self.assertEqual(worker.poll_once(now=134.9), 0)
        self.assertEqual(worker.poll_once(now=135), 1)
        self.assertFalse(path.exists())
        lp_calls = [call.args[0] for call in run.call_args_list if call.args[0][0] == "lp"]
        self.assertEqual(lp_calls[0][4], "hp-color")

    @patch("app.services.document_service.subprocess.run")
    def test_hotfolder_keeps_a_complete_pdf_when_cups_rejects_it(self, run):
        def reject(args, **_kwargs):
            if args[0] == "lp":
                return subprocess.CompletedProcess(args, 1, "", "printer unavailable")
            return self.lpstat(args)

        run.side_effect = reject
        worker = DocumentHotfolderService(
            self.service,
            stable_seconds=1,
            poll_seconds=1,
            retry_seconds=30,
        )
        path = self.jobs / "retry.pdf"
        path.write_bytes(b"%PDF-1.7\n%%EOF\n")

        worker.poll_once(now=10)
        self.assertEqual(worker.poll_once(now=11), 0)
        self.assertTrue(path.exists())
        self.assertEqual(worker.poll_once(now=20), 0)
        self.assertEqual(
            len([call for call in run.call_args_list if call.args[0][0] == "lp"]),
            1,
        )

    @patch("app.services.document_service.subprocess.run")
    def test_missing_print_client_is_not_reported_as_timeout(self, run):
        run.side_effect = FileNotFoundError("lp")

        with self.assertRaisesRegex(DocumentPrintError, "print client is not installed"):
            self.service._run(["lp"])

    @patch("app.services.document_service.subprocess.run")
    def test_print_timeout_is_reported_as_timeout(self, run):
        run.side_effect = subprocess.TimeoutExpired(["lp"], 60)

        with self.assertRaisesRegex(DocumentPrintError, "did not respond in time"):
            self.service._run(["lp"])

    @patch("app.services.document_service.subprocess.run")
    def test_print_client_os_error_is_reported_as_connection_error(self, run):
        run.side_effect = PermissionError("not permitted")

        with self.assertRaisesRegex(DocumentPrintError, "could not be contacted"):
            self.service._run(["lp"])


class EditorDocumentTest(unittest.TestCase):
    def test_alignment_is_stored_without_csp_blocked_inline_styles(self):
        content = sanitize_editor_document(
            '<div style="text-align: center;"><b>Centered label</b></div>'
        )

        self.assertEqual(content, '<div align="center"><b>Centered label</b></div>')
        self.assertNotIn("style=", content)

    def test_nested_rich_text_formatting_is_preserved(self):
        content = sanitize_editor_document(
            '<u><font face="Arial, sans-serif" size="3"><b>Formatted</b></font></u>'
        )

        self.assertEqual(
            content,
            '<u><font face="Arial, sans-serif" size="3"><b>Formatted</b></font></u>',
        )

    def test_bundled_label_font_is_preserved(self):
        content = sanitize_editor_document(
            '<font face="\'DejaVu Sans Condensed\', sans-serif" size="5">Narrow label</font>'
        )

        self.assertEqual(
            content,
            '<font face="&#x27;DejaVu Sans Condensed&#x27;, sans-serif" size="5">Narrow label</font>',
        )

    def test_positioned_image_coordinates_are_validated(self):
        tiny_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        content = sanitize_editor_document(
            '<span class="editor-image-wrap" data-image-size="small" '
            'data-image-x="12.5" data-image-y="8.25" data-image-width="31.75" style="left:999px">'
            f'<img src="data:image/png;base64,{tiny_png}"></span>'
        )

        self.assertIn('data-image-x="12.5"', content)
        self.assertIn('data-image-y="8.25"', content)
        self.assertIn('data-image-width="31.75"', content)
        self.assertNotIn("style=", content)

    def test_positioned_text_box_coordinates_and_formatting_are_preserved(self):
        content = sanitize_editor_document(
            '<div class="editor-text-wrap" data-text-x="17.5" '
            'data-text-y="22.25" data-text-width="48.75" '
            'data-text-height="32.5" style="left:999px">'
            '<div class="editor-text-box" contenteditable="true">'
            '<font face="Georgia, serif" size="5"><u>Movable text</u></font>'
            '</div></div>'
        )

        self.assertIn('class="editor-text-wrap"', content)
        self.assertIn('data-text-x="17.5"', content)
        self.assertIn('data-text-y="22.25"', content)
        self.assertIn('data-text-width="48.75"', content)
        self.assertIn('data-text-height="32.5"', content)
        self.assertIn('class="editor-text-box" contenteditable="true"', content)
        self.assertIn('<font face="Georgia, serif" size="5"><u>Movable text</u></font>', content)
        self.assertNotIn("style=", content)


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
        expected_date = datetime.fromtimestamp(source.stat().st_mtime).strftime("%Y-%m-%d")
        self.assertEqual(len(self.service.list()), 1)
        renamed = self.service.rename(source.name, "Electricity bill", "date")
        self.assertEqual(renamed, f"{expected_date} Electricity bill.pdf")
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
        self.root = root
        printer_config = root / "printers.json"
        printer_config.write_text(json.dumps(CONFIG), encoding="utf-8")

        class Overrides:
            TESTING = True
            WTF_CSRF_ENABLED = False
            UI_LANGUAGE = "en"
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

        documents = self.client.get("/documents")
        self.assertNotIn(b"Print waiting PDFs", documents.data)
        self.assertEqual(self.client.post("/documents/api/print-jobs").status_code, 404)

    def test_saved_labels_and_scanned_pdfs_are_local_drawers(self):
        labels = self.client.get("/labels").data
        scans = self.client.get("/scans").data

        self.assertIn(b'aria-controls="labelLibraryDrawer"', labels)
        self.assertIn(b'id="labelLibraryDrawer"', labels)
        self.assertNotIn(b"Scanned PDFs", labels)
        self.assertIn(b'aria-controls="scanFilesDrawer"', scans)
        self.assertIn(b'id="scanFilesDrawer"', scans)
        self.assertNotIn(b"Saved labels", scans)

    def test_every_page_has_the_theme_switch(self):
        for path in ("/", "/documents", "/labels", "/scans"):
            response = self.client.get(path)
            self.assertIn(b'id="themeToggle"', response.data, path)
            self.assertIn(b'aria-label="Switch to light mode"', response.data, path)

    def test_pwa_assets_are_linked_and_service_worker_has_root_scope(self):
        response = self.client.get("/")

        self.assertIn(b'rel="manifest"', response.data)
        self.assertIn(b'/manifest.webmanifest', response.data)
        self.assertIn(b'/static/js/pwa.js', response.data)

        manifest = self.client.get("/manifest.webmanifest")
        self.assertEqual(manifest.mimetype, "application/manifest+json")
        self.assertEqual(manifest.json["lang"], "en")
        self.assertEqual(manifest.json["start_url"], "/")
        self.assertEqual(manifest.json["scope"], "/")
        self.assertEqual(manifest.json["display"], "standalone")

        service_worker = self.client.get("/service-worker.js")
        self.assertEqual(service_worker.status_code, 200)
        self.assertEqual(service_worker.mimetype, "application/javascript")
        self.assertEqual(service_worker.headers["Cache-Control"], "no-cache")
        self.assertEqual(service_worker.headers["Service-Worker-Allowed"], "/")
        self.assertIn(b'const UI_LANGUAGE = "en"', service_worker.data)
        service_worker.close()

    def test_german_language_setting_covers_templates_javascript_and_pwa(self):
        self.app.config["UI_LANGUAGE"] = "de"

        home = self.client.get("/")
        documents = self.client.get("/documents")
        labels = self.client.get("/labels")
        scans = self.client.get("/scans")
        translations = self.client.get("/ui-translations.js")
        manifest = self.client.get("/manifest.webmanifest")
        service_worker = self.client.get("/service-worker.js")

        self.assertIn(b'<html lang="de">', home.data)
        self.assertIn("Was möchtest du tun?".encode(), home.data)
        self.assertIn("Wähle eine Funktion aus.".encode(), home.data)
        self.assertIn(b"PDFs hier ablegen", documents.data)
        self.assertIn(b"PDFs hinzuf\xc3\xbcgen", documents.data)
        self.assertIn(b"Gespeicherte Etiketten", labels.data)
        self.assertIn(b"Symbole", labels.data)
        self.assertIn("Zerbrechlich".encode(), labels.data)
        self.assertIn(b"Bereit zum Scannen", scans.data)
        self.assertIn("Drucker werden geladen".encode(), translations.data)
        self.assertEqual(manifest.json["lang"], "de")
        self.assertEqual(manifest.json["short_name"], "Drucken & Scannen")
        self.assertIn(b'const UI_LANGUAGE = "de"', service_worker.data)

        scanner = self.app.extensions["scanner_client"]
        with patch.object(
            scanner,
            "status",
            return_value={
                "state": "error",
                "error": "No pages were scanned. Check the feeder and try again.",
            },
        ):
            status = self.client.get("/scans/api/status")
        self.assertIn("Es wurden keine Seiten gescannt".encode(), status.data)

    def test_unknown_language_falls_back_to_english(self):
        self.assertEqual(normalize_language(None), "en")
        self.assertEqual(normalize_language("fr"), "en")
        self.assertEqual(normalize_language(" DE "), "de")

    def test_scanned_pdf_can_be_sent_to_a_document_printer(self):
        path = self.root / "scans" / "searchable.pdf"
        path.write_bytes(b"%PDF-1.7\n%%EOF\n")
        service = self.app.extensions["document_print_service"]

        with patch.object(
            service,
            "print_preserved_pdf",
            return_value="Brother MFC-L2710DW",
        ) as print_pdf:
            response = self.client.post(
                "/scans/api/files/searchable.pdf/print",
                json={"printer": "mfc"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Brother MFC-L2710DW", response.data)
        print_pdf.assert_called_once_with("mfc", path)


if __name__ == "__main__":
    unittest.main()
