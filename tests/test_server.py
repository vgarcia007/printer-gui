from __future__ import annotations

import http.client
import json
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from app.server import PrintError, PrinterConfig, PrinterHTTPServer, PrintService, make_handler


CONFIG = {
    "version": 1,
    "defaultPrinter": "hp-color",
    "printers": [
        {
            "name": "mfc",
            "label": "Brother MFC-L2710DW",
            "uri": "http://192.0.2.10",
            "driver": "brother.ppd",
            "options": {"PageSize": "A4"},
        },
        {
            "name": "hp-color",
            "label": "HP Color Laser MFP 178nw",
            "uri": "socket://192.0.2.20",
            "driver": "hp.ppd",
            "options": {"PageSize": "A4"},
        },
    ],
}


class FakeRunner:
    def __init__(self, fail_print: bool = False) -> None:
        self.fail_print = fail_print
        self.calls: list[list[str]] = []

    def run(
        self, args: list[str], *, timeout: int = 30, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        if args[0] == "lpstat":
            output = (
                "printer mfc is idle.  enabled since now\n"
                "printer hp-color is idle.  enabled since now\n"
                "system default destination: hp-color\n"
            )
            return subprocess.CompletedProcess(args, 0, output, "")
        if args[0] == "lpr" and self.fail_print:
            raise PrintError("printer unavailable")
        return subprocess.CompletedProcess(args, 0, "", "")


class ServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.jobs = self.root / "jobs"
        self.jobs.mkdir()
        self.config_path = self.root / "printers.json"
        self.config_path.write_text(json.dumps(CONFIG), encoding="utf-8")
        self.runner = FakeRunner()
        self.service = PrintService(
            self.jobs, self.config_path, "cups:631", runner=self.runner
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_configuration_selects_hp_as_default(self) -> None:
        config = PrinterConfig.load(self.config_path)
        self.assertEqual(config.default_printer, "hp-color")
        self.assertEqual([printer.name for printer in config.printers], ["mfc", "hp-color"])

    def test_status_lists_both_printers_and_only_regular_pdfs(self) -> None:
        (self.jobs / "A.pdf").write_bytes(b"%PDF-1.7\n")
        (self.jobs / "ignore.txt").write_text("not a PDF", encoding="utf-8")
        (self.jobs / "linked.pdf").symlink_to(self.jobs / "A.pdf")

        status = self.service.status()

        self.assertEqual(status["defaultPrinter"], "hp-color")
        self.assertEqual(status["jobs"], ["A.pdf"])
        self.assertEqual(
            [printer["name"] for printer in status["printers"]], ["mfc", "hp-color"]
        )

    def test_upload_is_sanitized_and_kept_as_pdf(self) -> None:
        path = self.service.save_upload("../invoice<script>.PDF", b"%PDF-1.7\nbody")

        self.assertEqual(path.parent, self.jobs.resolve())
        self.assertEqual(path.name, "invoice_script_.pdf")
        self.assertTrue(path.exists())

    def test_non_pdf_upload_is_rejected(self) -> None:
        with self.assertRaisesRegex(PrintError, "keine gültige PDF"):
            self.service.save_upload("notes.pdf", b"plain text")

    def test_successful_submission_deletes_file(self) -> None:
        pdf = self.jobs / "document.pdf"
        pdf.write_bytes(b"%PDF-1.7\n")

        self.assertEqual(self.service.print_files("hp-color", [pdf]), 1)
        self.assertFalse(pdf.exists())
        self.assertTrue(any(call[0] == "lpr" and "hp-color" in call for call in self.runner.calls))

    def test_failed_submission_retains_file(self) -> None:
        pdf = self.jobs / "document.pdf"
        pdf.write_bytes(b"%PDF-1.7\n")
        service = PrintService(
            self.jobs, self.config_path, "cups:631", runner=FakeRunner(fail_print=True)
        )

        with self.assertRaisesRegex(PrintError, "printer unavailable"):
            service.print_files("hp-color", [pdf])
        self.assertTrue(pdf.exists())


class HTTPTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.jobs = self.root / "jobs"
        self.jobs.mkdir()
        self.config_path = self.root / "printers.json"
        self.config_path.write_text(json.dumps(CONFIG), encoding="utf-8")
        self.service = PrintService(
            self.jobs, self.config_path, "cups:631", runner=FakeRunner()
        )
        static = self.root / "static"
        static.mkdir()
        (static / "index.html").write_text("<!doctype html><title>Test</title>", encoding="utf-8")
        self.server = PrinterHTTPServer(
            ("127.0.0.1", 0), make_handler(self.service, static)
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def request(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, bytes]:
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        payload = response.read()
        connection.close()
        return response.status, payload

    def test_health_and_status_endpoints(self) -> None:
        health_status, health = self.request("GET", "/health")
        api_status, payload = self.request("GET", "/api/status")

        self.assertEqual(health_status, 200)
        self.assertTrue(json.loads(health)["ok"])
        self.assertEqual(api_status, 200)
        self.assertEqual(json.loads(payload)["defaultPrinter"], "hp-color")

    def test_foreign_origin_is_rejected(self) -> None:
        status, payload = self.request(
            "POST",
            "/api/print-jobs",
            b"{}",
            {"Content-Type": "application/json", "Origin": "https://attacker.example"},
        )

        self.assertEqual(status, 403)
        self.assertFalse(json.loads(payload)["ok"])

    def test_static_path_cannot_escape_root(self) -> None:
        status, _ = self.request("GET", "/../printers.json")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
