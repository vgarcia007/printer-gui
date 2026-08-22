from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class TemplateError(ValueError):
    pass


@dataclass(frozen=True)
class LabelTemplate:
    id: str
    name: str
    width_mm: float
    height_mm: float
    safe_margin_mm: float
    orientations: tuple[str, ...]
    prompt_hint: str = ""
    orientation_dimensions: dict[str, tuple[float, float]] | None = None
    active: bool = True

    def dimensions_for(self, orientation: str) -> tuple[float, float]:
        if orientation not in self.orientations:
            raise TemplateError("This orientation is not supported by the template.")
        if self.orientation_dimensions and orientation in self.orientation_dimensions:
            return self.orientation_dimensions[orientation]
        if orientation == "portrait":
            return self.height_mm, self.width_mm
        return self.width_mm, self.height_mm


class TemplateService:
    REQUIRED_FIELDS = {
        "id",
        "name",
        "width_mm",
        "height_mm",
        "safe_margin_mm",
        "orientations",
    }

    def __init__(self, template_dir: str | Path):
        self.template_dir = Path(template_dir)
        self._templates = self._load()

    def _load(self) -> dict[str, LabelTemplate]:
        templates: dict[str, LabelTemplate] = {}
        if not self.template_dir.is_dir():
            raise TemplateError(
                f"Template directory not found: {self.template_dir}"
            )
        for path in sorted(self.template_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise TemplateError(f"Template {path.name} is invalid.") from exc
            missing = self.REQUIRED_FIELDS - data.keys()
            if missing:
                raise TemplateError(
                    f"Template {path.name} is missing required fields."
                )
            orientations = tuple(data["orientations"])
            if (
                not data["id"]
                or data["id"] in templates
                or not set(orientations).issubset({"landscape", "portrait"})
                or not orientations
            ):
                raise TemplateError(f"Template {path.name} is not plausible.")
            try:
                width = float(data["width_mm"])
                height = float(data["height_mm"])
                margin = float(data["safe_margin_mm"])
            except (TypeError, ValueError) as exc:
                raise TemplateError(f"Template {path.name} has invalid dimensions.") from exc
            orientation_dimensions: dict[str, tuple[float, float]] = {}
            try:
                for orientation, dimensions in data.get(
                    "orientation_dimensions", {}
                ).items():
                    if orientation not in orientations:
                        raise ValueError
                    orientation_dimensions[orientation] = (
                        float(dimensions["width_mm"]),
                        float(dimensions["height_mm"]),
                    )
            except (AttributeError, KeyError, TypeError, ValueError) as exc:
                raise TemplateError(
                    f"Template {path.name} has invalid orientation dimensions."
                ) from exc
            all_dimensions = [(width, height), *orientation_dimensions.values()]
            if (
                margin < 0
                or any(
                    item_width <= 0
                    or item_height <= 0
                    or margin * 2 >= min(item_width, item_height)
                    for item_width, item_height in all_dimensions
                )
            ):
                raise TemplateError(f"Template {path.name} has implausible dimensions.")
            templates[data["id"]] = LabelTemplate(
                id=data["id"],
                name=data["name"],
                width_mm=width,
                height_mm=height,
                safe_margin_mm=margin,
                orientations=orientations,
                prompt_hint=str(data.get("prompt_hint", "")),
                orientation_dimensions=orientation_dimensions or None,
                active=bool(data.get("active", True)),
            )
        if not templates:
            raise TemplateError("No label templates were found.")
        if not any(template.active for template in templates.values()):
            raise TemplateError("No active label template was found.")
        return templates

    def all(self) -> list[LabelTemplate]:
        return [template for template in self._templates.values() if template.active]

    def get(self, template_id: str) -> LabelTemplate:
        try:
            return self._templates[template_id]
        except KeyError as exc:
            raise TemplateError("Unknown label template.") from exc
