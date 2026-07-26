"""Persistent chat sessions."""

from __future__ import annotations

import time
import uuid
from typing import Any

from app.config import Settings
from app.storage.db import connect


async def ensure_session(settings: Settings, session_id: str | None) -> str:
    sid = (session_id or "").strip() or str(uuid.uuid4())
    now = time.time()
    db = await connect(settings)
    try:
        cur = await db.execute("SELECT id FROM sessions WHERE id = ?", (sid,))
        row = await cur.fetchone()
        if row:
            await db.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?", (now, sid)
            )
        else:
            await db.execute(
                "INSERT INTO sessions (id, created_at, updated_at) VALUES (?, ?, ?)",
                (sid, now, now),
            )
        await db.commit()
    finally:
        await db.close()
    return sid


async def append_message(
    settings: Settings, session_id: str, role: str, content: str
) -> None:
    now = time.time()
    db = await connect(settings)
    try:
        await db.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, now),
        )
        await db.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id)
        )
        await db.commit()
    finally:
        await db.close()
    await trim_session(settings, session_id)


async def get_history(settings: Settings, session_id: str) -> list[dict[str, Any]]:
    db = await connect(settings)
    try:
        cur = await db.execute(
            """
            SELECT role, content FROM messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        )
        rows = await cur.fetchall()
        return [{"role": r[0], "content": r[1]} for r in rows]
    finally:
        await db.close()


async def get_history_for_llm(
    settings: Settings,
    session_id: str,
    *,
    max_messages: int | None = None,
    max_chars: int = 6000,
) -> list[dict[str, Any]]:
    """Recent turns only, char-budgeted — conversation-memory short buffer."""
    hist = await get_history(settings, session_id)
    clean = [
        h
        for h in hist
        if h.get("role") in ("user", "assistant") and (h.get("content") or "").strip()
    ]
    limit = max_messages or min(settings.session_max_messages, 16)
    clean = clean[-limit:]
    # Truncate long individual messages (tool dumps in assistant text)
    out: list[dict[str, Any]] = []
    for h in clean:
        c = str(h["content"])
        if len(c) > 800:
            c = c[:780] + "…"
        out.append({"role": h["role"], "content": c})
    # Enforce total char budget from the end
    total = 0
    kept: list[dict[str, Any]] = []
    for h in reversed(out):
        n = len(h["content"])
        if total + n > max_chars and kept:
            break
        kept.append(h)
        total += n
    kept.reverse()
    return kept


async def trim_session(settings: Settings, session_id: str) -> None:
    max_n = settings.session_max_messages
    db = await connect(settings)
    try:
        cur = await db.execute(
            "SELECT id FROM messages WHERE session_id = ? ORDER BY id DESC",
            (session_id,),
        )
        ids = [r[0] for r in await cur.fetchall()]
        if len(ids) <= max_n:
            return
        drop = ids[max_n:]
        await db.executemany(
            "DELETE FROM messages WHERE id = ?", [(i,) for i in drop]
        )
        await db.commit()
    finally:
        await db.close()


async def clear_session(settings: Settings, session_id: str) -> None:
    db = await connect(settings)
    try:
        await db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await db.commit()
    finally:
        await db.close()
