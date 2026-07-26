"""Persistent user profile (SQLite). Single source of truth for identity prefs."""

from __future__ import annotations

from app.config import Settings
from app.core.identity import validate_display_name
from app.storage.db import connect

KEY_USER_NAME = "user_name"
# Allowlisted profile keys (entity-style prefs; no free-form dump)
ALLOWED_KEYS = frozenset({"user_name", "locale", "night_brightness"})


class ProfileError(Exception):
    pass


async def get_profile(settings: Settings) -> dict[str, str]:
    db = await connect(settings)
    try:
        cur = await db.execute("SELECT key, value FROM profile")
        rows = await cur.fetchall()
        return {str(r[0]): str(r[1]) for r in rows}
    finally:
        await db.close()


async def get_user_name(settings: Settings) -> str | None:
    prof = await get_profile(settings)
    raw = (prof.get(KEY_USER_NAME) or "").strip()
    if not raw:
        return None
    return validate_display_name(raw) or raw


async def set_user_name(settings: Settings, raw_name: str) -> str:
    name = validate_display_name(raw_name)
    if not name:
        raise ProfileError(
            "Geçersiz isim. Sadece harf kullan (2–24 karakter); 'ne/kim' soru değildir."
        )
    await set_profile(settings, KEY_USER_NAME, name)
    return name


async def set_profile(settings: Settings, key: str, value: str) -> None:
    key = (key or "").strip()
    if not key or len(key) > 64:
        raise ProfileError("Geçersiz profil anahtarı.")
    if key not in ALLOWED_KEYS:
        raise ProfileError(f"İzin verilmeyen profil anahtarı: {key}")
    value = (value or "").strip()
    if len(value) > 256:
        raise ProfileError("Profil değeri çok uzun.")
    db = await connect(settings)
    try:
        await db.execute(
            """
            INSERT INTO profile (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        await db.commit()
    finally:
        await db.close()


async def clear_user_name(settings: Settings) -> None:
    db = await connect(settings)
    try:
        await db.execute("DELETE FROM profile WHERE key = ?", (KEY_USER_NAME,))
        await db.commit()
    finally:
        await db.close()
