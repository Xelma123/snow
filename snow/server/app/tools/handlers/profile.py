"""User profile tools — validated server-side."""

from __future__ import annotations

from typing import Any

from app.storage import profile as profile_store
from app.tools.context import ToolContext


async def profile_get(ctx: ToolContext, args: dict[str, Any]) -> Any:
    key = str(args.get("key") or "user_name")
    if key == "user_name":
        uname = await profile_store.get_user_name(ctx.settings)
        return {"key": key, "user_name": uname}
    prof = await profile_store.get_profile(ctx.settings)
    return {"key": key, "value": prof.get(key)}


async def profile_set(ctx: ToolContext, args: dict[str, Any]) -> Any:
    try:
        uname = await profile_store.set_user_name(
            ctx.settings, str(args.get("user_name") or "")
        )
    except profile_store.ProfileError as e:
        return {"error": str(e)}
    return {"ok": True, "user_name": uname}
