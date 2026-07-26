"""Data-driven multi-step macros from personal/routines.yaml."""

from __future__ import annotations

import json
from typing import Any

from app.tools.context import ToolContext
from app.tools.routines import get_routine, list_routine_summaries


async def list_routines(ctx: ToolContext, args: dict[str, Any]) -> Any:
    return {"routines": list_routine_summaries(ctx.settings)}


async def run_routine(ctx: ToolContext, args: dict[str, Any]) -> Any:
    routine_id = str(args.get("routine_id") or "")
    routine = get_routine(ctx.settings, routine_id)
    if not routine:
        return {
            "error": f"Rutin bulunamadı: {routine_id}",
            "available": [r["id"] for r in list_routine_summaries(ctx.settings)],
        }
    if not ctx.run_tool:
        return {"error": "run_tool bağlı değil"}

    steps = routine.get("steps") or []
    results: list[dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        tool = str(step.get("tool") or "")
        step_args = step.get("args") or {}
        if not isinstance(step_args, dict):
            step_args = {}
        if tool in ("run_routine", "list_routines"):
            results.append({"tool": tool, "error": "nested routine yok"})
            continue
        raw = await ctx.run_tool(tool, step_args)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"raw": raw}
        results.append({"tool": tool, "args": step_args, "result": parsed})
        if isinstance(parsed, dict) and parsed.get("error"):
            return {
                "ok": False,
                "routine_id": routine.get("id"),
                "title": routine.get("title"),
                "stopped": True,
                "steps": results,
            }
    return {
        "ok": True,
        "routine_id": routine.get("id"),
        "title": routine.get("title"),
        "steps": results,
    }
