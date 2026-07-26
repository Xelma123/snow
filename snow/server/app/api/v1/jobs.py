from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.deps import require_token
from app.storage import jobs as job_store

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
async def list_jobs(_: None = Depends(require_token)) -> dict:
    settings = get_settings()
    items = await job_store.list_pending(settings)
    return {"jobs": items}


class CancelBody(BaseModel):
    job_id: int


@router.delete("/{job_id}")
async def cancel_job(job_id: int, _: None = Depends(require_token)) -> dict:
    settings = get_settings()
    ok = await job_store.cancel(settings, job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="İş bulunamadı veya zaten bitti")
    return {"ok": True, "job_id": job_id}
