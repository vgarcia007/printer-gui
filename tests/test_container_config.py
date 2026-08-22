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


if __name__ == "__main__":
    unittest.main()
