from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.deps import require_token
from app.integrations.ha import HomeAssistant
from app.tools.registry import ToolExecutor
from app.tools.routines import get_routine, list_routine_summaries

router = APIRouter(prefix="/routines", tags=["routines"])


@router.get("")
async def list_routines(_: None = Depends(require_token)) -> dict:
    return {"routines": list_routine_summaries(get_settings())}


class RunBody(BaseModel):
    routine_id: str = Field(..., min_length=1)


@router.post("/run")
async def run_routine(body: RunBody, _: None = Depends(require_token)) -> dict:
    settings = get_settings()
    if not get_routine(settings, body.routine_id):
        raise HTTPException(status_code=404, detail="Rutin bulunamadı")
    tools = ToolExecutor(settings, HomeAssistant(settings))
    import json

    raw = await tools.run("run_routine", {"routine_id": body.routine_id})
    return json.loads(raw)
