import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CUPSContainerConfigTestCase(unittest.TestCase):
    def test_queues_are_visible_to_web_on_private_compose_network(self) -> None:
        entrypoint = (ROOT / "cups" / "entrypoint.sh").read_text()
        compose = (ROOT / "compose.yaml").read_text()

        self.assertIn("-o printer-is-shared=true", entrypoint)
        self.assertNotIn('"631:631"', compose)
        self.assertIn("WEB_PORT:-8081", compose)

    def test_repository_spool_remains_traversable_by_host_tools(self) -> None:
        entrypoint = (ROOT / "cups" / "entrypoint.sh").read_text()

        self.assertIn("chmod 0755 /var/spool/cups", entrypoint)

    def test_all_four_services_restart_and_ocr_has_no_persistent_work_volume(self) -> None:
        compose = (ROOT / "compose.yaml").read_text()

        self.assertEqual(compose.count("restart: unless-stopped"), 4)
        self.assertIn("/work:size=2g", compose)
        self.assertIn("read_only: true", compose)
        self.assertNotIn("ocr-data", compose)
        self.assertIn("HOTFOLDER_STABLE_SECONDS", compose)
        self.assertIn("JOBS_HOST_DIR:-./data/jobs", compose)
        self.assertIn('"--workers", "1"', (ROOT / "app" / "Dockerfile").read_text())

    def test_printer_configuration_uses_schema_two(self) -> None:
        import json

        config = json.loads((ROOT / "config" / "printers.json").read_text())
        self.assertEqual(config["version"], 2)
        self.assertEqual(config["labelPrinter"], "DYMO_LabelWriter_450")
        self.assertEqual(
            [item["kind"] for item in config["printers"]],
            ["document", "document", "label"],
        )

    def test_dymo_defaults_preserve_the_editor_artwork_at_one_to_one_scale(self) -> None:
        compose = (ROOT / "compose.yaml").read_text()
        css = (ROOT / "app" / "static" / "css" / "app.css").read_text()

        self.assertIn("DYMO_LANDSCAPE_OFFSET_MM:-0", compose)
        self.assertIn("DYMO_LANDSCAPE_SHRINK_MM:-0", compose)
        self.assertIn("DYMO_LANDSCAPE_START_TRIM_MM:-0", compose)
        self.assertIn("aspect-ratio:88/34", css)
        self.assertIn("inset:2mm", css)
        self.assertIn("padding:2mm", css)

    def test_label_editor_uses_exact_dom_capture_and_familiar_controls(self) -> None:
        template = (ROOT / "app" / "templates" / "labels" / "editor.html").read_text()
        javascript = (ROOT / "app" / "static" / "js" / "editor.js").read_text()
        css = (ROOT / "app" / "static" / "css" / "app.css").read_text()

        self.assertLess(template.index("editor-toolbar"), template.index("label-stage"))
        self.assertIn('id="insertImage"', template)
        self.assertIn("Image size", template)
        self.assertIn("editor-statusbar", template)
        self.assertIn("window.html2canvas(editor", javascript)
        self.assertIn("normalizedDocument(content)", javascript)
        self.assertNotIn("context.fillText", javascript)
        self.assertIn("scale: printDpi / cssDpi", javascript)
        self.assertIn('output.width = outputWidth', javascript)
        self.assertIn('context.drawImage(renderedEditor, 0, 0)', javascript)
        self.assertIn("width:88mm;height:34mm", css)
        self.assertIn("padding:2mm", css)
        self.assertIn("font-size:10pt", css)
        self.assertIn(".label-canvas u,.label-canvas u *", css)
        self.assertIn("@page dymo-30321{size:88mm 34mm;margin:0}", css)
        self.assertIn('class="label-stage label-sheet"', template)
        self.assertIn("html2canvas/releases/download/v1.4.1", (ROOT / "app" / "Dockerfile").read_text())

    def test_interface_uses_self_hosted_font_awesome_icons(self) -> None:
        dockerfile = (ROOT / "app" / "Dockerfile").read_text()
        base = (ROOT / "app" / "templates" / "base.html").read_text()
        templates = "\n".join(
            path.read_text() for path in (ROOT / "app" / "templates").rglob("*.html")
        )

        self.assertIn("Font-Awesome/5.15.4/css/all.min.css", dockerfile)
        self.assertIn("Font-Awesome/5.15.4/webfonts/fa-regular-400.woff2", dockerfile)
        self.assertIn("Font-Awesome/5.15.4/webfonts/fa-solid-900.woff2", dockerfile)
        self.assertIn("--checksum=sha256:99464ceb71bc9bbdcc72275faefe44f98eb5cbb6b5d8ee665b87b35376f1a96e", dockerfile)
        self.assertIn("vendor/fontawesome/css/all.min.css", base)
        self.assertIn('class="app-header"', base)
        self.assertIn('class="desktop-nav"', base)
        self.assertIn('class="mobile-nav"', base)
        self.assertIn('class="far fa-file-pdf"', templates)
        self.assertIn('class="fas fa-file-import"', templates)
        self.assertIn('class="fas fa-bold"', templates)
        self.assertNotIn("<svg", templates)
        for replaced_symbol in ("▤", "▰", "▱", "→"):
            self.assertNotIn(replaced_symbol, templates)

    def test_scan_interface_has_clear_states_and_inline_pdf_management(self) -> None:
        template = (ROOT / "app" / "templates" / "scans" / "index.html").read_text()
        scan_javascript = (ROOT / "app" / "static" / "js" / "scans.js").read_text()
        files_javascript = (ROOT / "app" / "static" / "js" / "scan-files.js").read_text()
        drawer_javascript = (ROOT / "app" / "static" / "js" / "drawers.js").read_text()

        self.assertIn('id="scanStatusIcon"', template)
        self.assertIn('id="scanFilesDrawer"', template)
        self.assertIn('fa-smile', scan_javascript)
        self.assertIn('fa-hourglass-half', scan_javascript)
        self.assertIn('fa-brain', scan_javascript)
        self.assertIn('fa-check-circle', scan_javascript)
        self.assertIn('className = "rename-panel"', files_javascript)
        self.assertIn('["none", "No prefix"]', files_javascript)
        self.assertIn('["date", "Date prefix"]', files_javascript)
        self.assertIn('["datetime", "Date & time prefix"]', files_javascript)
        self.assertIn('event.key === "Escape"', drawer_javascript)

    def test_libraries_use_page_local_drawers_instead_of_header_navigation(self) -> None:
        base = (ROOT / "app" / "templates" / "base.html").read_text()
        labels = (ROOT / "app" / "templates" / "labels" / "editor.html").read_text()
        scans = (ROOT / "app" / "templates" / "scans" / "index.html").read_text()
        label_drawer = (ROOT / "app" / "templates" / "labels" / "_library_drawer.html").read_text()

        self.assertNotIn('class="library-nav"', base)
        self.assertNotIn("labels.gallery", base)
        self.assertIn('aria-controls="labelLibraryDrawer"', labels)
        self.assertIn('id="labelLibraryDrawer"', label_drawer)
        self.assertIn('aria-controls="scanFilesDrawer"', scans)
        self.assertIn('data-drawer-scrim="scanFilesDrawer"', scans)


if __name__ == "__main__":
    unittest.main()
