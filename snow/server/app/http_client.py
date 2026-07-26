"""Shared async HTTP client for HA / Open-Meteo."""

from __future__ import annotations

import httpx

_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(25.0, connect=8.0))
    return _client


async def startup_http() -> None:
    get_http_client()


async def shutdown_http() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None
