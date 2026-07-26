"""Load named routines from personal/routines.yaml — data-driven macros."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.config import Settings

_cache: dict[str, Any] | None = None
_mtime: float | None = None


def _path(settings: Settings) -> Path:
    # devices.yaml sibling
    return Path(settings.devices_file).resolve().parent / "routines.yaml"


def load_routines(settings: Settings) -> dict[str, Any]:
    global _cache, _mtime
    path = _path(settings)
    if not path.is_file():
        return {}
    mt = path.stat().st_mtime
    if _cache is not None and _mtime == mt:
        return _cache
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    routines = raw.get("routines") or raw
    if not isinstance(routines, dict):
        routines = {}
    _cache = routines
    _mtime = mt
    return routines


def list_routine_summaries(settings: Settings) -> list[dict[str, str]]:
    out = []
    for key, body in load_routines(settings).items():
        if not isinstance(body, dict):
            continue
        out.append(
            {
                "id": key,
                "title": str(body.get("title") or key),
                "description": str(body.get("description") or ""),
            }
        )
    return out


def get_routine(settings: Settings, routine_id: str) -> dict[str, Any] | None:
    rid = (routine_id or "").strip().lower()
    routines = load_routines(settings)
    # exact
    if rid in routines and isinstance(routines[rid], dict):
        return {"id": rid, **routines[rid]}
    # match title / aliases
    for key, body in routines.items():
        if not isinstance(body, dict):
            continue
        aliases = [key, str(body.get("title") or "").lower()]
        aliases += [str(a).lower() for a in (body.get("aliases") or [])]
        if rid in aliases or any(rid in a or a in rid for a in aliases if a):
            return {"id": key, **body}
    return None
