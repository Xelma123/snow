"""Home inventory and scene tools."""

from __future__ import annotations

from typing import Any

from app.integrations.ha import HomeAssistantError
from app.tools.context import ToolContext


async def list_entities(ctx: ToolContext, args: dict[str, Any]) -> Any:
    domain = str(args.get("domain", "light"))
    return {"entities": await ctx.ha.list_by_domain(domain)}


async def list_scenes(ctx: ToolContext, args: dict[str, Any]) -> Any:
    return {"scenes": await ctx.ha.list_by_domain("scene")}


async def activate_scene(ctx: ToolContext, args: dict[str, Any]) -> Any:
    eid = ctx.resolve(str(args.get("entity_id", "")), None)
    if not eid:
        raise HomeAssistantError("scene entity_id gerekli")
    return await ctx.ha.activate_scene(eid)


async def home_summary(ctx: ToolContext, args: dict[str, Any]) -> Any:
    return await ctx.ha.home_summary()


async def answer_only(ctx: ToolContext, args: dict[str, Any]) -> Any:
    return {"ok": True, "note": args.get("note", "")}
