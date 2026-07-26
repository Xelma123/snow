"""PC control tool handler — WOL / status / agent desktop."""

from __future__ import annotations

from typing import Any

from app.integrations.pc import (
    PcError,
    pc_agent_desktop,
    pc_agent_macro,
    pc_agent_power,
    pc_status,
    pc_wake,
    resolve_pc,
)
from app.tools.context import ToolContext

# Actions that need the Windows agent (machine must be awake)
_AGENT_POWER = frozenset({"sleep", "shutdown", "reboot"})
_AGENT_DESKTOP = frozenset(
    {"lock", "volume", "mute", "unmute", "open_url", "close_tab", "open_app"}
)


async def pc_control(ctx: ToolContext, args: dict[str, Any]) -> Any:
    action = str(args.get("action") or "").strip().lower()
    target = args.get("target")
    value = args.get("value")

    try:
        pc_id, pc = resolve_pc(ctx.settings, str(target) if target else None)
    except PcError as e:
        return {"error": str(e)}

    try:
        if action == "status":
            return await pc_status(ctx.settings, pc, pc_id)
        if action == "wake":
            return await pc_wake(ctx.settings, pc, pc_id)
        if action in _AGENT_POWER:
            return await pc_agent_power(ctx.settings, pc, pc_id, action)
        if action in _AGENT_DESKTOP:
            # volume uses value as 0-100
            if action == "volume" and value is not None:
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    return {"error": "volume değeri 0–100 sayı olmalı"}
            return await pc_agent_desktop(
                ctx.settings, pc, pc_id, action, value
            )
        if action == "run_macro":
            mid = str(value or "").strip()
            if not mid:
                return {"error": "run_macro için value=makro_id gerekli"}
            return await pc_agent_macro(ctx.settings, pc, pc_id, mid)
        return {"error": f"Bilinmeyen pc action: {action}"}
    except PcError as e:
        return {"error": str(e), "pc_id": pc_id, "action": action}
