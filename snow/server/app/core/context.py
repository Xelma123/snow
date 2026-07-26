"""Dynamic runtime context for the agent — live house state, not static strings."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.config import Settings
from app.integrations.ha import HomeAssistant
from app.storage import jobs as job_store
from app.storage import profile as profile_store
from app.tools.routines import list_routine_summaries

logger = logging.getLogger("snow.context")

# Short TTL cache so every chat doesn't hammer HA (still dynamic, not static forever)
_cache: dict[str, Any] = {"ts": 0.0, "summary": None}
_TTL = 20.0


async def build_world_context(settings: Settings) -> dict[str, Any]:
    """Fresh-ish snapshot of home + user profile + jobs for the LLM."""
    now = time.time()
    summary: dict[str, Any] | None = _cache.get("summary")
    if not summary or now - float(_cache.get("ts") or 0) > _TTL:
        try:
            summary = await HomeAssistant(settings).home_summary()
            _cache["summary"] = summary
            _cache["ts"] = now
        except Exception as e:  # noqa: BLE001
            logger.warning("world context HA failed: %s", e)
            summary = {"error": str(e), "lights": [], "media_players": [], "counts": {}}

    user_name = None
    try:
        user_name = await profile_store.get_user_name(settings)
    except Exception as e:  # noqa: BLE001
        logger.warning("profile read failed: %s", e)

    pending_jobs: list[dict[str, Any]] = []
    try:
        pending_jobs = await job_store.list_pending(settings, limit=8)
    except Exception as e:  # noqa: BLE001
        logger.warning("jobs list failed: %s", e)

    routines = []
    try:
        routines = list_routine_summaries(settings)
    except Exception as e:  # noqa: BLE001
        logger.warning("routines list failed: %s", e)

    return {
        "user_name": user_name,
        "home": summary,
        "defaults": {
            "light": settings.ha_default_light,
            "tv": settings.ha_default_tv,
        },
        "pending_jobs": pending_jobs,
        "routines": routines,
    }


def format_world_for_prompt(world: dict[str, Any]) -> str:
    """Compact dynamic inventory block injected every turn."""
    home = world.get("home") or {}
    lines = ["## CANLI EV ENVANTERİ (her tur güncellenir — uydurma)"]
    un = world.get("user_name")
    lines.append(f"- Kayıtlı kullanıcı adı: {un if un else '(yok)'}")
    d = world.get("defaults") or {}
    lines.append(f"- Varsayılan light: {d.get('light')}")
    lines.append(f"- Varsayılan tv: {d.get('tv')}")

    if home.get("error"):
        lines.append(f"- HA erişim uyarısı: {home['error']}")
        return "\n".join(lines)

    counts = home.get("counts") or {}
    lines.append(
        f"- Sayımlar: light={counts.get('lights', 0)}, "
        f"switch={counts.get('switches', 0)}, "
        f"media={counts.get('media_players', 0)}, "
        f"scene={counts.get('scenes', 0)}"
    )

    def _fmt(entities: list, limit: int = 8) -> str:
        parts = []
        for e in (entities or [])[:limit]:
            parts.append(
                f"{e.get('entity_id')} [{e.get('state')}] "
                f"\"{e.get('name', '')}\""
            )
        return "; ".join(parts) if parts else "(yok)"

    lines.append(f"- Lights: {_fmt(home.get('lights') or [])}")
    lines.append(f"- Media: {_fmt(home.get('media_players') or [])}")
    lines.append(f"- Switches: {_fmt(home.get('switches') or [], 6)}")
    if home.get("default_light"):
        dl = home["default_light"]
        lines.append(
            f"- Aktif varsayılan ışık: {dl.get('entity_id')} "
            f"state={dl.get('state')} bri={dl.get('brightness_pct')}"
        )
    if home.get("default_tv"):
        tv = home["default_tv"]
        lines.append(
            f"- Aktif varsayılan TV: {tv.get('entity_id')} state={tv.get('state')}"
        )

    jobs = world.get("pending_jobs") or []
    if jobs:
        jparts = [
            f"#{j.get('id')} in {j.get('in_seconds')}s: {j.get('label')}"
            for j in jobs[:5]
        ]
        lines.append(f"- Bekleyen işler: {'; '.join(jparts)}")
    else:
        lines.append("- Bekleyen işler: (yok)")

    routines = world.get("routines") or []
    if routines:
        rparts = [f"{r.get('id')} ({r.get('title')})" for r in routines[:8]]
        lines.append(f"- Rutinler: {', '.join(rparts)}")
    return "\n".join(lines)


def invalidate_home_cache() -> None:
    _cache["ts"] = 0.0
    _cache["summary"] = None
