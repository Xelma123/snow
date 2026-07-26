"""Shared context passed into every tool handler."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import Settings
from app.integrations.ha import HomeAssistant
from app.tools.aliases import resolve_entity


@dataclass
class ToolContext:
    settings: Settings
    ha: HomeAssistant
    # Bound by executor for nested calls (e.g. run_routine steps)
    run_tool: Any = None  # async (name, args) -> str (JSON)

    def light_id(self, args: dict[str, Any]) -> str | None:
        raw = args.get("entity_id")
        return resolve_entity(
            self.settings,
            str(raw) if raw else None,
            self.settings.ha_default_light,
        )

    def media_id(self, args: dict[str, Any]) -> str | None:
        raw = args.get("entity_id")
        if raw:
            return resolve_entity(self.settings, str(raw), None)
        return resolve_entity(self.settings, "tv", self.settings.ha_default_tv or None)

    def resolve(self, entity_id: str | None, default: str | None = None) -> str | None:
        return resolve_entity(self.settings, entity_id, default)
