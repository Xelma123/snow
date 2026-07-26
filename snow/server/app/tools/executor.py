"""ToolExecutor — dispatch table over handlers + mutate cache invalidation."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import Settings
from app.integrations.ha import HomeAssistant, HomeAssistantError
from app.tools.context import ToolContext
from app.tools.handlers import HANDLERS
from app.tools.manifest import is_home_mutating
from app.tools.validation import ValidationFail, validate_tool_args

logger = logging.getLogger("snow.tools")


class ToolExecutor:
    def __init__(self, settings: Settings, ha: HomeAssistant) -> None:
        self.settings = settings
        self.ha = ha
        self._ctx = ToolContext(settings=settings, ha=ha, run_tool=self.run)

    async def run(self, name: str, arguments: dict[str, Any] | str) -> str:
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments or "{}")
            except json.JSONDecodeError:
                return json.dumps(
                    {
                        "error": "Araç argümanları geçerli JSON değil",
                        "validation": True,
                        "tool": name,
                    },
                    ensure_ascii=False,
                )
        if not isinstance(arguments, dict):
            arguments = {}
        try:
            clean = validate_tool_args(name, arguments)
        except ValidationFail as e:
            logger.info("tool validation failed %s: %s", name, e.message)
            return json.dumps(
                {"error": e.message, "validation": True, "tool": name},
                ensure_ascii=False,
            )
        try:
            result = await self._dispatch(name, clean)
            if is_home_mutating(name) and not (
                isinstance(result, dict) and result.get("error")
            ):
                from app.core.context import invalidate_home_cache

                invalidate_home_cache()
            return json.dumps(result, ensure_ascii=False)
        except HomeAssistantError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        except Exception as e:  # noqa: BLE001
            logger.exception("tool %s failed", name)
            return json.dumps({"error": f"Araç hatası: {e}"}, ensure_ascii=False)

    async def _dispatch(self, name: str, args: dict[str, Any]) -> Any:
        handler = HANDLERS.get(name)
        if not handler:
            return {"error": f"Bilinmeyen araç: {name}"}
        return await handler(self._ctx, args)
