"""Tool audit log."""

from __future__ import annotations

import time

from app.config import Settings
from app.storage.db import connect


async def log_tool(
    settings: Settings,
    session_id: str | None,
    tool: str,
    arguments: str,
    result: str,
) -> None:
    db = await connect(settings)
    try:
        await db.execute(
            """
            INSERT INTO audit (session_id, tool, arguments, result, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                tool,
                (arguments or "")[:2000],
                (result or "")[:4000],
                time.time(),
            ),
        )
        await db.commit()
    finally:
        await db.close()
