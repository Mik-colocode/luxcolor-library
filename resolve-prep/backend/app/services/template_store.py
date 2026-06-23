from __future__ import annotations

import json
from pathlib import Path

from app.config import settings
from app.models.templates import PrepTemplate


class TemplateStore:
    def __init__(self, templates_dir: Path | None = None) -> None:
        self.templates_dir = templates_dir or settings.templates_dir

    def list_templates(self) -> list[PrepTemplate]:
        templates: list[PrepTemplate] = []
        if not self.templates_dir.exists():
            return templates
        for path in sorted(self.templates_dir.glob("*.json")):
            templates.append(self.load(path.stem))
        return templates

    def load(self, template_id: str) -> PrepTemplate:
        path = self.templates_dir / f"{template_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Template not found: {template_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return PrepTemplate.model_validate(data)

    def save(self, template: PrepTemplate) -> PrepTemplate:
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        path = self.templates_dir / f"{template.id}.json"
        path.write_text(
            template.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return template
