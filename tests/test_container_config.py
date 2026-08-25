import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


class CUPSContainerConfigTestCase(unittest.TestCase):
    def test_queues_are_visible_to_web_on_private_compose_network(self) -> None:
        entrypoint = (ROOT / "cups" / "entrypoint.sh").read_text()
        compose = (ROOT / "compose.yaml").read_text()

        self.assertIn("-o printer-is-shared=true", entrypoint)
        self.assertNotIn('"631:631"', compose)
        self.assertIn("WEB_PORT:-8081", compose)
        self.assertIn("UI_LANGUAGE: ${UI_LANGUAGE:-en}", compose)

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
        self.assertIn('id="insertText"', template)
        self.assertIn('id="fontPickerMenu"', template)
        self.assertEqual(template.count('class="font-picker-option '), 7)
        self.assertIn('id="insertSymbol"', template)
        self.assertIn('id="symbolPalette"', template)
        self.assertEqual(template.count('class="symbol-choice"'), 16)
        self.assertIn('id="deleteSelected"', template)
        self.assertNotIn('id="imageTools"', template)
        self.assertNotIn('id="textTools"', template)
        self.assertIn("editor-statusbar", template)
        self.assertIn("const fitImageToLabel = wrapper =>", javascript)
        self.assertIn("maximumHeight * aspectRatio", javascript)
        self.assertIn('["nw", "ne", "sw", "se"]', javascript)
        self.assertIn("const startImageResize = (event, wrapper, corner) =>", javascript)
        self.assertIn("const renderSymbolImage = async glyphCode =>", javascript)
        self.assertIn("const createTextBox = (", javascript)
        self.assertIn("const startTextMove = (event, wrapper) =>", javascript)
        self.assertIn("const startTextResize = (event, wrapper, corner) =>", javascript)
        self.assertIn("const growTextBoxToContent = wrapper =>", javascript)
        self.assertIn("const canStartPointerDrag = event =>", javascript)
        self.assertIn('event.pointerType !== "mouse"', javascript)
        self.assertIn('["nw", "ne", "sw", "se"].forEach(corner =>', javascript)
        self.assertIn("migrateLegacyText();", javascript)
        self.assertIn('insertImage(await renderSymbolImage(button.dataset.symbolGlyph), "small")', javascript)
        self.assertIn("wrapper.dataset.imageWidth", javascript)
        self.assertIn('querySelectorAll(".image-resize-handle,.text-box-control")', javascript)
        self.assertIn(".editor-image-wrap.is-selected .image-resize-handle{display:block}", css)
        self.assertIn(".editor-text-wrap.is-selected .text-box-control{display:grid}", css)
        self.assertIn("@media(pointer:coarse)", css)
        self.assertIn(".image-resize-handle,.text-resize-handle{width:30px;height:30px", css)
        self.assertIn(".font-preview-dejavu-condensed", css)
        self.assertIn('@font-face{font-family:"DejaVu Sans Condensed"', css)
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

    def test_label_fonts_are_bundled_in_the_web_container(self) -> None:
        dockerfile = (ROOT / "app" / "Dockerfile").read_text()
        template = (ROOT / "app" / "templates" / "labels" / "editor.html").read_text()

        self.assertIn("fonts-dejavu-core fonts-dejavu-extra", dockerfile)
        self.assertIn("/static/vendor/fonts/dejavu", dockerfile)
        for family in ("DejaVu Sans", "DejaVu Sans Condensed", "DejaVu Serif", "DejaVu Sans Mono"):
            self.assertIn(family, template)

    def test_scan_interface_has_clear_states_and_inline_pdf_management(self) -> None:
        template = (ROOT / "app" / "templates" / "scans" / "index.html").read_text()
        print_modal = (ROOT / "app" / "templates" / "scans" / "_print_modal.html").read_text()
        scan_javascript = (ROOT / "app" / "static" / "js" / "scans.js").read_text()
        files_javascript = (ROOT / "app" / "static" / "js" / "scan-files.js").read_text()
        drawer_javascript = (ROOT / "app" / "static" / "js" / "drawers.js").read_text()
        css = (ROOT / "app" / "static" / "css" / "app.css").read_text()

        self.assertIn('id="scanStatusIcon"', template)
        self.assertIn('id="scanFilesDrawer"', template)
        self.assertIn('class="editor-heading"', template)
        self.assertIn('class="scan-workbench"', template)
        self.assertIn('class="scan-status-card"', template)
        self.assertIn('class="scan-action-panel"', template)
        self.assertIn('id="scanPrintModal"', print_modal)
        self.assertLess(template.index("scan-status-card"), template.index("scan-action-panel"))
        self.assertIn('fa-smile', scan_javascript)
        self.assertIn('fa-hourglass-half', scan_javascript)
        self.assertIn('fa-brain', scan_javascript)
        self.assertIn('fa-check-circle', scan_javascript)
        self.assertIn('className = "rename-panel"', files_javascript)
        self.assertIn('loadAll({ force: true })', files_javascript)
        self.assertIn('root.querySelector(".rename-panel")', files_javascript)
        self.assertIn('completion !== refreshedCompletion', scan_javascript)
        self.assertIn('.rename-cancel{border-radius:.25rem 0 0 .25rem;color:#212529;background:#fff}', css)
        self.assertIn('iconButton("fa-print", t("Print"), "fas")', files_javascript)
        self.assertIn('pendingPrintFile.filename) + "/print"', files_javascript)
        self.assertIn('dateStyle: "medium"', files_javascript)
        self.assertIn('timeStyle: "short"', files_javascript)
        self.assertNotIn("formatSize", files_javascript)
        self.assertIn('["none", t("No prefix")]', files_javascript)
        self.assertIn('["date", t("Date prefix")]', files_javascript)
        self.assertIn('["datetime", t("Date & time prefix")]', files_javascript)
        self.assertIn('event.key === "Escape"', drawer_javascript)

    def test_document_interface_uses_the_shared_workbench_layout(self) -> None:
        template = (ROOT / "app" / "templates" / "documents" / "index.html").read_text()
        css = (ROOT / "app" / "static" / "css" / "app.css").read_text()
        javascript = (ROOT / "app" / "static" / "js" / "documents.js").read_text()

        self.assertIn('class="editor-view document-view"', template)
        self.assertIn('class="editor-heading"', template)
        self.assertIn('class="document-workbench"', template)
        self.assertIn('class="document-upload-frame"', template)
        self.assertIn('class="document-action-panel"', template)
        self.assertIn('id="fileInput" class="visually-hidden" type="file" accept="application/pdf,.pdf" multiple', template)
        self.assertIn('id="fileQueue"', template)
        self.assertIn('id="progressView"', template)
        self.assertIn('class="document-print-animation"', template)
        self.assertLess(template.index("document-upload-frame"), template.index("document-action-panel"))
        self.assertIn(".label-editor-form,.scan-workbench,.document-workbench", css)
        self.assertIn(".editor-footer,.scan-action-panel,.document-action-panel", css)
        self.assertIn("@keyframes paper-feed", css)
        self.assertIn("files.push(...pdfs.map", javascript)
        self.assertIn("for (let index = 0; index < completedFiles.length; index += 1)", javascript)
        self.assertIn("await request(url", javascript)
        self.assertIn("MINIMUM_PRINT_ANIMATION_MS = 20_000", javascript)
        self.assertIn("await wait(remainingAnimationTime)", javascript)
        self.assertLess(javascript.index("for (let index = 0"), javascript.index("renderResult(completedFiles)"))

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

    def test_theme_switch_defaults_to_dark_and_persists_light_mode(self) -> None:
        base = (ROOT / "app" / "templates" / "base.html").read_text()
        theme_javascript = (ROOT / "app" / "static" / "js" / "theme.js").read_text()
        css = (ROOT / "app" / "static" / "css" / "app.css").read_text()

        self.assertIn('id="themeToggle"', base)
        self.assertIn('role="switch"', base)
        self.assertLess(base.index("js/theme.js"), base.index("css/app.css"))
        self.assertIn('initialTheme = storedTheme === "light" ? "light" : "dark"', theme_javascript)
        self.assertIn('window.localStorage.setItem(storageKey', theme_javascript)
        self.assertIn('html[data-theme="light"]', css)
        self.assertIn("--app-bg:#212529", css)

    def test_pwa_manifest_icons_and_safe_service_worker_strategy(self) -> None:
        service_worker = (ROOT / "app" / "static" / "service-worker.js").read_text()
        base = (ROOT / "app" / "templates" / "base.html").read_text()

        self.assertIn('rel="manifest"', base)
        self.assertIn("url_for('web_manifest')", base)
        self.assertIn("js/pwa.js", base)
        self.assertIn('const UI_LANGUAGE = "__UI_LANGUAGE__"', service_worker)
        self.assertIn("print-scan-hub-shell-v10", service_worker)
        self.assertIn("offline-${UI_LANGUAGE}.html", service_worker)
        self.assertIn('request.method !== "GET"', service_worker)
        self.assertIn('url.pathname.includes("/api/")', service_worker)

        for size in (192, 512):
            with Image.open(ROOT / "app" / "static" / "icons" / f"icon-{size}.png") as icon:
                self.assertEqual(icon.size, (size, size))
            with Image.open(ROOT / "app" / "static" / "icons" / f"icon-maskable-{size}.png") as icon:
                self.assertEqual(icon.size, (size, size))

    def test_apache_example_contains_only_placeholders(self) -> None:
        apache = (ROOT / "deploy" / "apache-vhost.example.conf").read_text()

        self.assertIn("ServerName <APP_HOSTNAME>", apache)
        self.assertIn("<TLS_FULLCHAIN_PATH>", apache)
        self.assertIn("<TLS_PRIVATE_KEY_PATH>", apache)
        self.assertIn("Require ip <TRUSTED_NETWORK>", apache)
        self.assertIn("127.0.0.1:<LOCAL_APP_PORT>", apache)
        self.assertNotIn("freilinger", apache.lower())
        self.assertNotIn("192.168.", apache)


if __name__ == "__main__":
    unittest.main()
