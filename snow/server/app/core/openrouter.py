"""OpenRouter client — fixed model, shared HTTP client."""

from __future__ import annotations

import logging
from typing import Any

from app.config import OPENROUTER_BASE_URL, OPENROUTER_MODEL, Settings
from app.http_client import get_http_client

logger = logging.getLogger("snow.openrouter")


class OpenRouterError(Exception):
    pass


async def chat_completion(
    settings: Settings,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not settings.openrouter_api_key:
        raise OpenRouterError("OPENROUTER_API_KEY eksik.")

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/local/snow",
        "X-Title": "Snow",
    }
    body: dict[str, Any] = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": 0.25,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"

    client = get_http_client()
    try:
        r = await client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=body,
            timeout=90.0,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("openrouter network: %s", type(e).__name__)
        raise OpenRouterError(f"OpenRouter ağ hatası: {type(e).__name__}") from e

    if r.status_code >= 400:
        # Never log full body with potential secrets; truncate
        logger.warning("openrouter HTTP %s", r.status_code)
        raise OpenRouterError(f"OpenRouter {r.status_code}: {r.text[:400]}")
    return r.json()
