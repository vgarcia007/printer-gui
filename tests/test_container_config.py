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
        self.assertIn("inset:5.88% 2.27%", css)
        self.assertIn("padding:2.27%", css)

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
        self.assertIn("@page dymo-30321{size:88mm 34mm;margin:0}", css)
        self.assertIn('class="label-stage label-sheet"', template)
        self.assertIn("html2canvas/releases/download/v1.4.1", (ROOT / "app" / "Dockerfile").read_text())


if __name__ == "__main__":
    unittest.main()
