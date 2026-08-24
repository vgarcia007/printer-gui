import unittest

from scanner.page_order import PageCountMismatch, assemble_pages


class ScannerPageOrderTests(unittest.TestCase):
    def test_simplex_pages_keep_their_order_and_drop_blanks(self):
        pages = assemble_pages(
            ["front-1", "front-2", "front-3"],
            None,
            lambda page: page == "front-2",
        )

        self.assertEqual(pages, ["front-1", "front-3"])

    def test_duplex_pages_are_paired_before_blank_sides_are_removed(self):
        pages = assemble_pages(
            ["front-1", "front-2"],
            ["back-2", "back-1"],
            lambda page: page == "back-1",
        )

        self.assertEqual(pages, ["front-1", "front-2", "back-2"])

    def test_duplex_pages_are_returned_in_document_order(self):
        pages = assemble_pages(
            ["front-1", "front-2"],
            ["back-2", "back-1"],
            lambda _page: False,
        )

        self.assertEqual(pages, ["front-1", "back-1", "front-2", "back-2"])

    def test_raw_duplex_count_mismatch_is_reported(self):
        with self.assertRaises(PageCountMismatch) as raised:
            assemble_pages(
                ["front-1", "front-2"],
                ["back-1"],
                lambda _page: False,
            )

        self.assertEqual(raised.exception.front_count, 2)
        self.assertEqual(raised.exception.back_count, 1)

    def test_fully_blank_scan_keeps_one_page(self):
        pages = assemble_pages(
            ["front-1", "front-2"],
            None,
            lambda _page: True,
        )

        self.assertEqual(pages, ["front-1"])


if __name__ == "__main__":
    unittest.main()
