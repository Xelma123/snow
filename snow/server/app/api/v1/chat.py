from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.agent import handle_chat
from app.deps import rate_limit, require_token

logger = logging.getLogger("snow.chat")
router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    actions: list = Field(default_factory=list)
    model: str = ""
    error: str | None = None
    fallback: bool | None = None
    home_snapshot: dict | None = None
    path: str | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    _: None = Depends(require_token),
    __: None = Depends(rate_limit),
) -> ChatResponse:
    try:
        raw = await handle_chat(body.message, body.session_id)
        return ChatResponse(
            session_id=str(raw.get("session_id") or "unknown"),
            reply=str(raw.get("reply") or ""),
            actions=list(raw.get("actions") or []),
            model=str(raw.get("model") or ""),
            error=raw.get("error"),
            fallback=raw.get("fallback"),
            home_snapshot=raw.get("home_snapshot"),
            path=raw.get("path"),
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("chat endpoint crash")
        return ChatResponse(
            session_id=body.session_id or "error",
            reply=f"Sunucu hatası: {e}",
            actions=[],
            model="",
            error=str(e),
            path="error",
        )
