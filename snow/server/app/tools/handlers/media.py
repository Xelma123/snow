"""Media player / TV control."""

from __future__ import annotations

from typing import Any

from app.tools.context import ToolContext


async def media_control(ctx: ToolContext, args: dict[str, Any]) -> Any:
    return await ctx.ha.media_control(
        entity_id=ctx.media_id(args),
        action=str(args.get("action", "on")),
        volume_level=args.get("volume_level"),
    )
