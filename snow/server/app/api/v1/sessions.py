from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import get_settings
from app.deps import require_token
from app.storage import sessions as session_store

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.delete("/{session_id}")
async def clear(session_id: str, _: None = Depends(require_token)) -> dict:
    await session_store.clear_session(get_settings(), session_id)
    return {"cleared": session_id}
