"""Scheduled jobs list / cancel."""

from __future__ import annotations

from typing import Any

from app.storage import jobs as job_store
from app.tools.context import ToolContext


async def list_jobs(ctx: ToolContext, args: dict[str, Any]) -> Any:
    return {"jobs": await job_store.list_pending(ctx.settings)}


async def cancel_job(ctx: ToolContext, args: dict[str, Any]) -> Any:
    jid = int(args.get("job_id") or 0)
    ok = await job_store.cancel(ctx.settings, jid)
    return {"ok": ok, "job_id": jid}
