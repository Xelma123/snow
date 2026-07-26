"""Light and switch actuators."""

from __future__ import annotations

from typing import Any

from app.integrations.ha import HomeAssistantError
from app.tools.context import ToolContext


async def get_home_state(ctx: ToolContext, args: dict[str, Any]) -> Any:
    return await ctx.ha.light_snapshot(ctx.light_id(args))


async def light_control(ctx: ToolContext, args: dict[str, Any]) -> Any:
    return await ctx.ha.light_control(
        entity_id=ctx.light_id(args),
        action=str(args.get("action", "on")),
        brightness_abs=args.get("brightness_abs"),
        brightness_delta=args.get("brightness_delta"),
        color_temp_kelvin=args.get("color_temp_kelvin"),
        rgb_color=args.get("rgb_color"),
    )


async def switch_control(ctx: ToolContext, args: dict[str, Any]) -> Any:
    eid = ctx.resolve(str(args.get("entity_id", "")), None)
    if not eid:
        raise HomeAssistantError("switch entity_id gerekli")
    return await ctx.ha.switch_control(eid, str(args.get("action", "toggle")))
