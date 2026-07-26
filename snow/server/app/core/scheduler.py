"""Background job runner — delayed light/TV commands with claim."""

from __future__ import annotations

import asyncio
import logging
import time

from app.config import Settings, get_settings
from app.integrations.ha import HomeAssistant
from app.storage import jobs as job_store
from app.tools.registry import ToolExecutor

logger = logging.getLogger("snow.scheduler")
_task: asyncio.Task | None = None


async def _tick(settings: Settings) -> None:
    due = await job_store.claim_due(settings)
    if not due:
        return
    ha = HomeAssistant(settings)
    tools = ToolExecutor(settings, ha)
    for job in due:
        payload = job.get("payload") or {}
        tool = payload.get("tool")
        args = payload.get("args") or {}
        jid = job["id"]
        t0 = time.time()
        try:
            if tool:
                result = await tools.run(tool, args)
                logger.info(
                    "job %s ran %s in %.2fs -> %s",
                    jid,
                    tool,
                    time.time() - t0,
                    (result or "")[:200],
                )
            await job_store.mark_done(settings, jid, ok=True)
        except Exception:  # noqa: BLE001
            logger.exception("job %s failed", jid)
            await job_store.mark_done(settings, jid, ok=False)


async def _loop() -> None:
    while True:
        try:
            await _tick(get_settings())
        except Exception:  # noqa: BLE001
            logger.exception("scheduler tick error")
        await asyncio.sleep(12)


def start_scheduler() -> None:
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_loop())
        logger.info("scheduler started")


async def stop_scheduler() -> None:
    global _task
    if _task and not _task.done():
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
    _task = None
