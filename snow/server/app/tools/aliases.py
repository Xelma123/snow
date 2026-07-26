"""Device aliases from personal/devices.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.config import Settings

_cache: dict[str, Any] | None = None
_cache_mtime: float | None = None


def load_aliases(settings: Settings) -> dict[str, str]:
    """Map lowercase alias -> entity_id."""
    global _cache, _cache_mtime
    path = Path(settings.devices_file)
    if not path.is_file():
        return {}
    mtime = path.stat().st_mtime
    if _cache is not None and _cache_mtime == mtime:
        return _cache  # type: ignore[return-value]

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    devices = raw.get("devices") or raw
    out: dict[str, str] = {}
    if isinstance(devices, dict):
        for alias, entity in devices.items():
            if isinstance(alias, str) and isinstance(entity, str):
                out[alias.strip().lower()] = entity.strip()
    _cache = out
    _cache_mtime = mtime
    return out


def resolve_entity(
    settings: Settings, name_or_id: str | None, default: str | None = None
) -> str | None:
    if not name_or_id:
        return default
    text = name_or_id.strip()
    if "." in text and not text.startswith(" "):
        # already entity-like
        if text.split(".", 1)[0] in {"light", "switch", "scene", "media_player"}:
            return text
    aliases = load_aliases(settings)
    key = text.lower()
    if key in aliases:
        return aliases[key]
    # partial match
    for alias, eid in aliases.items():
        if alias in key or key in alias:
            return eid
    return text if "." in text else default


def aliases_for_prompt(settings: Settings) -> str:
    aliases = load_aliases(settings)
    if not aliases:
        return "(alias tanımlı değil — personal/devices.yaml)"
    lines = [f"- {a} → {e}" for a, e in sorted(aliases.items())]
    return "\n".join(lines)
