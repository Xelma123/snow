"""Auth + rate limiting."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request

from app.config import get_settings

_hits: dict[str, deque[float]] = defaultdict(deque)
_MAX_KEYS = 500


def require_token(authorization: str | None = Header(default=None)) -> None:
    settings = get_settings()
    expected = settings.snow_app_token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token gerekli")
    token = authorization.removeprefix("Bearer ").strip()
    if token != expected:
        raise HTTPException(status_code=403, detail="Geçersiz token")


def rate_limit(request: Request, authorization: str | None = Header(default=None)) -> None:
    settings = get_settings()
    limit = settings.rate_limit_per_minute
    key = (authorization or "")[:80] + "|" + (request.client.host if request.client else "?")
    now = time.time()
    q = _hits[key]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(status_code=429, detail="Çok fazla istek — bir dakika bekle.")
    q.append(now)
    # prune map
    if len(_hits) > _MAX_KEYS:
        stale = [k for k, v in _hits.items() if not v or now - v[-1] > 120]
        for k in stale[:200]:
            _hits.pop(k, None)
