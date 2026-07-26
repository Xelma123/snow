from __future__ import annotations

from fastapi import APIRouter, Query

from app.config import OPENROUTER_MODEL, get_settings, validate_settings
from app.integrations.ha import HomeAssistant, HomeAssistantError

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(deep: bool = Query(False)) -> dict:
    settings = get_settings()
    warnings = validate_settings(settings)
    body: dict = {
        "ok": True,
        "name": "snow",
        "version": "1.0.0",
        "model": OPENROUTER_MODEL,
        "ha_url": settings.ha_url,
        "token_is_default": settings.weak_token,
        "openrouter_configured": bool(settings.openrouter_api_key),
        "ha_token_configured": bool(settings.ha_token),
        "warnings": warnings,
        "rule_fallback": settings.enable_rule_fallback,
        "features": [
            "lights",
            "tv_media",
            "weather_place",
            "multi_intent",
            "delayed_jobs",
            "profile_name",
            "busy_ui",
        ],
    }
    if deep:
        ha_ok = False
        ha_detail = None
        try:
            ha_detail = await HomeAssistant(settings).ping()
            ha_ok = True
        except HomeAssistantError as e:
            ha_detail = str(e)
            body["ok"] = False
        except Exception as e:  # noqa: BLE001
            ha_detail = str(e)
            body["ok"] = False
        body["deep"] = {"home_assistant": {"ok": ha_ok, "detail": ha_detail}}
    return body
