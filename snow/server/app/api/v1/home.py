from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import get_settings
from app.deps import require_token
from app.integrations.ha import HomeAssistant, HomeAssistantError

router = APIRouter(prefix="/home", tags=["home"])


@router.get("/summary")
async def home_summary(_: None = Depends(require_token)) -> dict:
    settings = get_settings()
    try:
        return await HomeAssistant(settings).home_summary()
    except HomeAssistantError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/entities")
async def entities(
    domain: str = Query(
        "light", pattern="^(light|switch|scene|media_player)$"
    ),
    _: None = Depends(require_token),
) -> dict:
    settings = get_settings()
    try:
        items = await HomeAssistant(settings).list_by_domain(domain)
        return {"domain": domain, "entities": items}
    except HomeAssistantError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/light")
async def light_probe(_: None = Depends(require_token)) -> dict:
    settings = get_settings()
    try:
        return await HomeAssistant(settings).light_snapshot()
    except HomeAssistantError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
