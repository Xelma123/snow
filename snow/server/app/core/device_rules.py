"""Device actuator fast-path (TR + slang) — high-confidence ONLY.

Not for identity/chat. Identity → agent identity path.
Default path for ambiguous language → LLM + tools + live inventory.
"""

from __future__ import annotations

import re
import time
from typing import Any

from app.config import Settings
from app.integrations.ha import HomeAssistant
from app.storage import jobs as job_store
from app.tools.registry import ToolExecutor


def _fold(text: str) -> str:
    t = (text or "").casefold()
    for src, dst in (
        ("ı", "i"),
        ("ğ", "g"),
        ("ü", "u"),
        ("ş", "s"),
        ("ö", "o"),
        ("ç", "c"),
        ("â", "a"),
        ("î", "i"),
        ("û", "u"),
    ):
        t = t.replace(src, dst)
    return " ".join(t.split())


def split_intents(text: str) -> list[str]:
    parts = re.split(r"\s+(?:ve|and|&|bir de)\s+", text.strip(), flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]


def _parse_delay_seconds(t: str) -> int | None:
    m = re.search(
        r"(\d+)\s*(saniye|sn|dakika|dk|min|saat|hour|hr)(?:\s*sonra)?",
        t,
    )
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2)
    if unit in ("saniye", "sn"):
        return max(1, n)
    if unit in ("dakika", "dk", "min"):
        return max(1, n * 60)
    if unit in ("saat", "hour", "hr"):
        return max(1, n * 3600)
    return None


def _strip_delay_phrase(text: str) -> str:
    t = _fold(text)
    t = re.sub(
        r"\d+\s*(saniye|sn|dakika|dk|min|saat|hour|hr)(?:\s*sonra)?",
        " ",
        t,
    )
    t = re.sub(r"\bsonra\b", " ", t)
    return " ".join(t.split())


async def try_rule_fallback(
    settings: Settings, text: str
) -> dict[str, Any] | None:
    if not settings.enable_rule_fallback:
        return None

    folded = _fold(text)
    delay = _parse_delay_seconds(folded)
    if delay:
        residual = _strip_delay_phrase(text)
        if not residual:
            return None
        planned = await _match_single(settings, residual, execute=False)
        if not planned or not planned.get("plan"):
            return None
        plan = planned["plan"]
        run_at = time.time() + delay
        jid = await job_store.enqueue(
            settings,
            run_at,
            {"tool": plan["tool"], "args": plan["args"], "label": residual},
        )
        mins = delay // 60
        human = f"{mins} dk" if mins >= 1 else f"{delay} sn"
        return {
            "reply": f"Tamam — {human} sonra: {residual}",
            "actions": [
                {
                    "tool": "schedule",
                    "arguments": str({"job_id": jid, "in_sec": delay}),
                    "result": '{"ok":true}',
                }
            ],
            "fallback": True,
        }

    return await _match_single(settings, text, execute=True)


async def _match_single(
    settings: Settings, text: str, *, execute: bool = True
) -> dict[str, Any] | None:
    t = _fold(text)
    pad = f" {t} "

    ha = HomeAssistant(settings)
    tools = ToolExecutor(settings, ha)
    actions: list[dict[str, Any]] = []

    async def do(tool: str, args: dict[str, Any], reply: str) -> dict[str, Any]:
        if not execute:
            return {
                "reply": reply,
                "actions": [],
                "fallback": True,
                "plan": {"tool": tool, "args": args},
            }
        raw = await tools.run(tool, args)
        actions.append({"tool": tool, "arguments": str(args), "result": raw})
        return {"reply": reply, "actions": actions, "fallback": True}

    about_light = any(
        w in t
        for w in (
            "isik",
            "isigi",
            "ampul",
            "lamba",
            "light",
            "led",
            "ates",
            "atesi",
            "fire",
        )
    )
    slang_on = any(
        w in t
        for w in (
            "acuba",
            "acsan",
            "acsana",
            "yakiver",
            "yaksana",
            "bir ac",
            "bi ac",
            "bi yak",
        )
    )
    short = t in (
        "ac",
        "kapat",
        "yak",
        "sonder",
        "sondur",
        "off",
        "on",
        "kis",
        "parlak",
    )

    # Weather STRICT
    weather_intent = bool(
        re.search(r"\b(hava\s*(nasil|durumu|ne|raporu)|weather|sicaklik)\b", t)
        or re.search(r"\b[\w]+\s*(da|de|ta|te)\s*hava\b", t)
    )
    if weather_intent:
        place = None
        m = re.search(
            r"(.+?)\s*(?:da|de|te|ta)?\s*hava(?:\s*(?:nasil|durumu|ne))?",
            t,
        )
        if m:
            cand = m.group(1).strip()
            for drop in ("ya", "peki", "knk", "abi", "kardes", "bana", "bir"):
                if cand.startswith(drop + " "):
                    cand = cand[len(drop) + 1 :]
            if cand and cand not in (
                "ev",
                "burada",
                "disari",
                "nasil",
                "ne",
                "bugun",
                "simdi",
            ):
                place = cand
        return await do(
            "get_weather",
            {"place": place} if place else {},
            "Hava okundu.",
        )

    if any(
        w in t
        for w in ("ev nasil", "ev durumu", "home summary", "evin durumu", "ev ozeti")
    ):
        return await do("home_summary", {}, "Ev ozeti.")

    about_tv = any(
        w in t for w in ("tv", "televizyon", "televizon", "android tv", "androidtv")
    )
    if about_tv:
        if any(w in pad for w in (" kapat ", " off ", " sonder ")):
            return await do("media_control", {"action": "off"}, "TV kapatildi.")
        if any(w in pad for w in (" ac ", " yak ", " on ", " open ")) or t.endswith(
            " ac"
        ):
            return await do("media_control", {"action": "on"}, "TV acildi.")
        if "duraklat" in t or "pause" in t:
            return await do("media_control", {"action": "pause"}, "TV duraklatildi.")
        if "devam" in t or " play" in pad:
            return await do("media_control", {"action": "play"}, "TV oynatiliyor.")
        if "var mi" in t or "yok mu" in t:
            return await do(
                "list_entities", {"domain": "media_player"}, "TV listesi."
            )

    if about_light and any(w in t for w in ("durum", "ne durumda", "status")):
        return await do("get_home_state", {}, "Isik durumu.")

    want_off = (
        any(w in pad for w in (" kapat ", " sonder ", " sondur ", " off ", " kapa "))
        or t.endswith("kapat")
        or t.endswith("sonder")
        or t.endswith("sondur")
    )
    want_on = (
        any(w in pad for w in (" ac ", " yak ", " on ", " open "))
        or t in ("ac", "yak", "on")
        or slang_on
        or "ates yak" in t
        or "atesi yak" in t
    )

    if (about_light or short or slang_on or "ates" in t) and want_off:
        return await do("light_control", {"action": "off"}, "Isik kapatildi.")

    if (about_light or short or slang_on or "ates" in t) and want_on:
        return await do("light_control", {"action": "on"}, "Isik acildi.")

    if any(w in t for w in ("azicik kis", "birazcik kis", "ufak kis")):
        return await do(
            "light_control",
            {"action": "on", "brightness_delta": -10},
            "Biraz kisildi.",
        )

    if "biraz kis" in t or "kis biraz" in t or (about_light and " kis" in pad):
        return await do(
            "light_control",
            {"action": "on", "brightness_delta": -20},
            "Parlaklik dusuruldu.",
        )

    if any(w in t for w in ("azicik ac", "biraz parlak", "biraz ac")):
        return await do(
            "light_control",
            {"action": "on", "brightness_delta": 15},
            "Biraz acildi.",
        )

    if "yariya" in t or ("yari" in t and about_light):
        return await do(
            "light_control",
            {"action": "on", "brightness_abs": 50},
            "Parlaklik %50.",
        )

    m = re.search(r"(?:parlaklik|brightness|yuzde|%)\s*(\d{1,3})", t)
    if not m:
        m = re.search(r"(\d{1,3})\s*(?:yap|percent|%)", t)
    if m and (about_light or "parlak" in t or short):
        val = max(0, min(100, int(m.group(1))))
        return await do(
            "light_control",
            {"action": "on", "brightness_abs": val},
            f"Parlaklik %{val}.",
        )

    # —— PC / MSI (one-shot only; delayed jobs handled above) ——
    about_pc = any(
        w in t
        for w in (
            "msi",
            "bilgisayar",
            "bilgisayari",
            "bilgisayarim",
            " laptop",
            "pc ",
            " pc",
            "masaüstü",
            "masaustu",
        )
    ) or t.strip() in ("pc", "msi") or t.startswith("pc ") or t.endswith(" pc")

    if about_pc or "sekme" in t:
        # status
        if any(
            w in t
            for w in (
                "acik mi",
                "kapali mi",
                "durum",
                "status",
                "uyuyor mu",
                "calisiyor mu",
            )
        ):
            return await do(
                "pc_control",
                {"action": "status"},
                "Bilgisayar durumu.",
            )
        # wake
        if any(
            w in t
            for w in (
                "uyandir",
                "uyandır",
                "wake",
                "acil",
                "acilsin",
            )
        ) or (
            about_pc
            and want_on
            and "sekme" not in t
        ):
            return await do(
                "pc_control",
                {"action": "wake"},
                "Bilgisayar uyandirma sinyali.",
            )
        # sleep
        if any(w in t for w in ("uyut", "uyku", "sleep", "uykuya")):
            return await do(
                "pc_control",
                {"action": "sleep"},
                "Bilgisayar uykuya.",
            )
        # shutdown
        if about_pc and want_off and "sekme" not in t:
            return await do(
                "pc_control",
                {"action": "shutdown"},
                "Bilgisayar kapatiliyor.",
            )
        # reboot
        if any(w in t for w in ("yeniden baslat", "reboot", "restart")):
            return await do(
                "pc_control",
                {"action": "reboot"},
                "Bilgisayar yeniden baslatiliyor.",
            )
        # lock
        if any(w in t for w in ("kilitle", "kilit", "lock")):
            return await do(
                "pc_control",
                {"action": "lock"},
                "Bilgisayar kilitleniyor.",
            )
        # close tab
        if "sekme" in t and any(w in t for w in ("kapat", "kapa", "close")):
            return await do(
                "pc_control",
                {"action": "close_tab"},
                "Sekme kapatma.",
            )

    # Identity is handled in agent identity path — never here.
    return None
