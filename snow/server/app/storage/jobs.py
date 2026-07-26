"""Deferred home commands (e.g. 5 dakika sonra ışığı kapat)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.config import Settings
from app.storage.db import connect

logger = logging.getLogger("snow.jobs")


async def enqueue(
    settings: Settings, run_at: float, payload: dict[str, Any]
) -> int:
    db = await connect(settings)
    try:
        cur = await db.execute(
            """
            INSERT INTO jobs (run_at, payload, status, created_at)
            VALUES (?, ?, 'pending', ?)
            """,
            (run_at, json.dumps(payload, ensure_ascii=False), time.time()),
        )
        await db.commit()
        return int(cur.lastrowid or 0)
    finally:
        await db.close()


async def fetch_due(settings: Settings, now: float | None = None) -> list[dict[str, Any]]:
    """Legacy read-only peek of due jobs (no claim). Prefer claim_due for runners."""
    now = now if now is not None else time.time()
    db = await connect(settings)
    try:
        cur = await db.execute(
            """
            SELECT id, payload FROM jobs
            WHERE status = 'pending' AND run_at <= ?
            ORDER BY run_at ASC
            LIMIT 20
            """,
            (now,),
        )
        rows = await cur.fetchall()
        out = []
        for r in rows:
            try:
                payload = json.loads(r[1])
            except json.JSONDecodeError:
                payload = {}
            out.append({"id": r[0], "payload": payload})
        return out
    finally:
        await db.close()


async def claim_due(
    settings: Settings, now: float | None = None, limit: int = 10
) -> list[dict[str, Any]]:
    """Atomically mark due pending jobs as running and return them."""
    now = now if now is not None else time.time()
    db = await connect(settings)
    try:
        cur = await db.execute(
            """
            SELECT id, payload FROM jobs
            WHERE status = 'pending' AND run_at <= ?
            ORDER BY run_at ASC
            LIMIT ?
            """,
            (now, limit),
        )
        rows = await cur.fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            jid = int(r[0])
            claim = await db.execute(
                """
                UPDATE jobs SET status = 'running'
                WHERE id = ? AND status = 'pending'
                """,
                (jid,),
            )
            if (claim.rowcount or 0) < 1:
                continue
            try:
                payload = json.loads(r[1])
            except json.JSONDecodeError:
                payload = {}
            out.append({"id": jid, "payload": payload})
        await db.commit()
        return out
    finally:
        await db.close()


async def mark_done(settings: Settings, job_id: int, ok: bool = True) -> None:
    db = await connect(settings)
    try:
        await db.execute(
            "UPDATE jobs SET status = ?, done_at = ? WHERE id = ?",
            ("done" if ok else "failed", time.time(), job_id),
        )
        await db.commit()
    finally:
        await db.close()


async def list_pending(settings: Settings, limit: int = 20) -> list[dict[str, Any]]:
    db = await connect(settings)
    try:
        cur = await db.execute(
            """
            SELECT id, run_at, payload, created_at FROM jobs
            WHERE status = 'pending'
            ORDER BY run_at ASC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cur.fetchall()
        out: list[dict[str, Any]] = []
        now = time.time()
        for r in rows:
            # id, run_at, payload, created_at
            try:
                payload = json.loads(r[2])
            except Exception:  # noqa: BLE001
                payload = {}
            run_at = float(r[1])
            pl = payload if isinstance(payload, dict) else {}
            label = str(pl.get("label") or pl.get("tool") or "job")
            out.append(
                {
                    "id": int(r[0]),
                    "run_at": run_at,
                    "in_seconds": max(0, int(run_at - now)),
                    "payload": pl,
                    "label": label,
                    "created_at": float(r[3] or 0),
                }
            )
        return out
    finally:
        await db.close()


async def cancel(settings: Settings, job_id: int) -> bool:
    db = await connect(settings)
    try:
        cur = await db.execute(
            """
            UPDATE jobs SET status = 'cancelled', done_at = ?
            WHERE id = ? AND status = 'pending'
            """,
            (time.time(), job_id),
        )
        await db.commit()
        return (cur.rowcount or 0) > 0
    finally:
        await db.close()

