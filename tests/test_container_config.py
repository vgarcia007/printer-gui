import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CUPSContainerConfigTestCase(unittest.TestCase):
    def test_queues_are_visible_to_web_on_private_compose_network(self) -> None:
        entrypoint = (ROOT / "cups" / "entrypoint.sh").read_text()
        compose = (ROOT / "compose.yaml").read_text()

        self.assertIn("-o printer-is-shared=true", entrypoint)
        self.assertNotIn('"631:631"', compose)

    def test_repository_spool_remains_traversable_by_host_tools(self) -> None:
        entrypoint = (ROOT / "cups" / "entrypoint.sh").read_text()

        self.assertIn("chmod 0755 /var/spool/cups", entrypoint)


if __name__ == "__main__":
    unittest.main()
