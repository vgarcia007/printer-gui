from __future__ import annotations

import base64
import binascii
from html import escape
from html.parser import HTMLParser
import re


class EditorDocumentError(ValueError):
    """A user-safe validation error for editable label documents."""


_IMAGE_DATA_RE = re.compile(
    r"^data:image/(?P<kind>png|jpeg);base64,(?P<data>[A-Za-z0-9+/]+={0,2})$"
)
_ALIGN_STYLE_RE = re.compile(
    r"^\s*text-align\s*:\s*(left|center|right)\s*;?\s*$",
    re.IGNORECASE,
)
_ALLOWED_TAGS = {"b", "strong", "i", "em", "u", "div", "p", "br", "font", "span", "img"}
_FONT_FACES = {
    "Arial, sans-serif",
    "'DejaVu Sans', sans-serif",
    '"DejaVu Sans", sans-serif',
    "DejaVu Sans, sans-serif",
    "'DejaVu Sans Condensed', sans-serif",
    '"DejaVu Sans Condensed", sans-serif',
    "DejaVu Sans Condensed, sans-serif",
    "Georgia, serif",
    "'DejaVu Serif', serif",
    '"DejaVu Serif", serif',
    "DejaVu Serif, serif",
    "'Courier New', monospace",
    '"Courier New", monospace',
    "Courier New, monospace",
    "'DejaVu Sans Mono', monospace",
    '"DejaVu Sans Mono", monospace',
    "DejaVu Sans Mono, monospace",
}
_IMAGE_SIZES = {"small", "medium", "large", "full"}
_IMAGE_COORDINATE_RE = re.compile(r"^(?:100(?:\.0{1,3})?|\d{1,2}(?:\.\d{1,3})?)$")


class _EditorDocumentSanitizer(HTMLParser):
    def __init__(self, max_image_bytes: int):
        super().__init__(convert_charrefs=True)
        self.max_image_bytes = max_image_bytes
        self.parts: list[str] = []
        self.has_content = False
        self.total_image_bytes = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag not in _ALLOWED_TAGS:
            return
        attributes = dict(attrs)
        clean_attributes: list[tuple[str, str]] = []

        if tag in {"div", "p"}:
            element_class = attributes.get("class", "")
            if tag == "div" and element_class == "editor-text-wrap":
                clean_attributes.append(("class", "editor-text-wrap"))
                for coordinate in ("x", "y"):
                    value = attributes.get(f"data-text-{coordinate}", "")
                    if _IMAGE_COORDINATE_RE.fullmatch(value):
                        clean_attributes.append((f"data-text-{coordinate}", value))
                width = attributes.get("data-text-width", "")
                if _IMAGE_COORDINATE_RE.fullmatch(width) and 15 <= float(width) <= 100:
                    clean_attributes.append(("data-text-width", width))
                clean_attributes.append(("contenteditable", "false"))
            elif tag == "div" and element_class == "editor-text-box":
                clean_attributes.extend(
                    [
                        ("class", "editor-text-box"),
                        ("contenteditable", "true"),
                    ]
                )
            style = attributes.get("style", "")
            match = _ALIGN_STYLE_RE.fullmatch(style)
            if match:
                clean_attributes.append(("align", match.group(1).lower()))
            align = attributes.get("align", "").lower()
            if align in {"left", "center", "right"} and not match:
                clean_attributes.append(("align", align))
        elif tag == "font":
            face = attributes.get("face", "")
            size = attributes.get("size", "")
            if face in _FONT_FACES:
                clean_attributes.append(("face", face))
            if size in {str(value) for value in range(1, 8)}:
                clean_attributes.append(("size", size))
        elif tag == "span":
            if attributes.get("class") == "editor-image-wrap":
                clean_attributes.append(("class", "editor-image-wrap"))
                size = attributes.get("data-image-size", "medium")
                clean_attributes.append(
                    ("data-image-size", size if size in _IMAGE_SIZES else "medium")
                )
                for coordinate in ("x", "y"):
                    value = attributes.get(f"data-image-{coordinate}", "")
                    if _IMAGE_COORDINATE_RE.fullmatch(value):
                        clean_attributes.append((f"data-image-{coordinate}", value))
                width = attributes.get("data-image-width", "")
                if _IMAGE_COORDINATE_RE.fullmatch(width) and 1 <= float(width) <= 84:
                    clean_attributes.append(("data-image-width", width))
                clean_attributes.append(("contenteditable", "false"))
        elif tag == "img":
            source = attributes.get("src", "")
            match = _IMAGE_DATA_RE.fullmatch(source)
            if not match:
                raise EditorDocumentError(
                    "A pasted image has an invalid format."
                )
            try:
                image_bytes = base64.b64decode(match.group("data"), validate=True)
            except (ValueError, binascii.Error) as exc:
                raise EditorDocumentError(
                    "A pasted image is damaged."
                ) from exc
            if match.group("kind") == "png":
                valid_signature = image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
            else:
                valid_signature = image_bytes.startswith(b"\xff\xd8")
            if not valid_signature:
                raise EditorDocumentError(
                    "A pasted image is damaged."
                )
            self.total_image_bytes += len(image_bytes)
            if self.total_image_bytes > self.max_image_bytes:
                raise EditorDocumentError(
                    "The pasted images are too large in total."
                )
            clean_attributes.extend(
                [
                    ("class", "editor-image"),
                    ("src", source),
                    ("alt", "Pasted image"),
                    ("draggable", "false"),
                ]
            )
            self.has_content = True

        rendered_attributes = "".join(
            f' {name}="{escape(value, quote=True)}"'
            for name, value in clean_attributes
        )
        self.parts.append(f"<{tag}{rendered_attributes}>")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _ALLOWED_TAGS and tag not in {"br", "img"}:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        self.parts.append(escape(data))
        if data.replace("\xa0", " ").strip():
            self.has_content = True


def sanitize_editor_document(
    content: str,
    *,
    max_length: int = 6 * 1024 * 1024,
    max_image_bytes: int = 5 * 1024 * 1024,
) -> str:
    if not isinstance(content, str) or not content:
        raise EditorDocumentError("The editable label document is missing.")
    if len(content) > max_length:
        raise EditorDocumentError("The label document is too large.")

    sanitizer = _EditorDocumentSanitizer(max_image_bytes=max_image_bytes)
    try:
        sanitizer.feed(content)
        sanitizer.close()
    except EditorDocumentError:
        raise
    except (TypeError, ValueError) as exc:
        raise EditorDocumentError(
            "The editable label document is invalid."
        ) from exc
    if not sanitizer.has_content:
        raise EditorDocumentError(
            "Enter text or paste an image from the clipboard."
        )
    return "".join(sanitizer.parts)
