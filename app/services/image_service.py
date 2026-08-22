from __future__ import annotations

from io import BytesIO
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError


class ImageValidationError(ValueError):
    """A user-safe validation error for generated raster labels."""


class ImageService:
    MIN_EDGE_PIXELS = 256

    def __init__(
        self,
        max_bytes: int = 20 * 1024 * 1024,
        max_pixels: int = 20_000_000,
        output_dpi: int = 300,
    ):
        self.max_bytes = int(max_bytes)
        self.max_pixels = int(max_pixels)
        self.output_dpi = int(output_dpi)
        if self.max_bytes <= 0 or self.max_pixels <= 0 or self.output_dpi <= 0:
            raise ValueError("PNG validation is configured incorrectly.")

    def pixel_dimensions(
        self, width_mm: float, height_mm: float
    ) -> tuple[int, int]:
        width = max(1, round(width_mm / 25.4 * self.output_dpi))
        height = max(1, round(height_mm / 25.4 * self.output_dpi))
        return width, height

    def validate_and_normalize(
        self,
        png_content: bytes,
        expected_width_mm: float,
        expected_height_mm: float,
    ) -> bytes:
        if not isinstance(png_content, bytes) or not png_content:
            raise ImageValidationError("The editor did not provide a PNG file.")
        if len(png_content) > self.max_bytes:
            raise ImageValidationError("The generated PNG file is too large.")

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(png_content)) as probe:
                    if probe.format != "PNG":
                        raise ImageValidationError(
                            "The generated file is not a valid PNG."
                        )
                    width, height = probe.size
                    if (
                        width < self.MIN_EDGE_PIXELS
                        or height < self.MIN_EDGE_PIXELS
                    ):
                        raise ImageValidationError(
                            "The generated PNG is too small to print."
                        )
                    if width * height > self.max_pixels:
                        raise ImageValidationError(
                            "The generated PNG contains too many pixels."
                        )
                    if getattr(probe, "is_animated", False) or getattr(
                        probe, "n_frames", 1
                    ) != 1:
                        raise ImageValidationError(
                            "Animated PNG files are not allowed."
                        )
                    probe.verify()

                with Image.open(BytesIO(png_content)) as source:
                    source.load()
                    source = ImageOps.exif_transpose(source)
                    if "A" in source.getbands():
                        rgba = source.convert("RGBA")
                        white = Image.new("RGBA", rgba.size, "white")
                        source = Image.alpha_composite(white, rgba).convert("L")
                    else:
                        source = source.convert("L")
        except ImageValidationError:
            raise
        except (
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
            UnidentifiedImageError,
            OSError,
            ValueError,
        ) as exc:
            raise ImageValidationError(
                "The generated PNG file is damaged or unsafe."
            ) from exc

        source = ImageOps.autocontrast(source)
        target_size = self.pixel_dimensions(
            expected_width_mm, expected_height_mm
        )
        fitted = ImageOps.contain(
            source,
            target_size,
            method=Image.Resampling.LANCZOS,
        )
        canvas = Image.new("L", target_size, "white")
        offset = (
            (target_size[0] - fitted.width) // 2,
            (target_size[1] - fitted.height) // 2,
        )
        canvas.paste(fitted, offset)

        output = BytesIO()
        canvas.save(
            output,
            format="PNG",
            optimize=True,
            dpi=(self.output_dpi, self.output_dpi),
        )
        normalized = output.getvalue()
        if len(normalized) > self.max_bytes:
            raise ImageValidationError("The normalized PNG is too large.")
        return normalized

    def preview(self, png_content: bytes, max_width: int) -> bytes:
        try:
            with Image.open(BytesIO(png_content)) as source:
                source.load()
                image = source.convert("L")
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ImageValidationError(
                "The PNG preview could not be read."
            ) from exc

        if image.width > max_width:
            target_height = max(1, round(image.height * max_width / image.width))
            image = image.resize(
                (max_width, target_height), Image.Resampling.LANCZOS
            )
        output = BytesIO()
        image.save(output, format="PNG", optimize=True)
        return output.getvalue()
