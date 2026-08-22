from io import BytesIO
import unittest

from PIL import Image, ImageChops

from app.services.label_print_service import LabelPrintService


class LabelPrintServiceTest(unittest.TestCase):
    def test_default_landscape_preparation_rotates_without_scaling_or_clipping(self):
        source = Image.new("L", (88, 34), "white")
        for x in range(source.width):
            for y in range(source.height):
                if x < 8 or y < 4:
                    source.putpixel((x, y), 0)

        png = BytesIO()
        source.save(png, format="PNG")

        printable, width_mm, height_mm = LabelPrintService.prepare_png_for_print(
            png.getvalue(), 88, 34
        )

        with Image.open(BytesIO(printable)) as result:
            expected = source.transpose(Image.Transpose.ROTATE_270)
            self.assertEqual(result.size, (34, 88))
            self.assertIsNone(ImageChops.difference(result, expected).getbbox())
        self.assertEqual((width_mm, height_mm), (34, 88))


if __name__ == "__main__":
    unittest.main()
