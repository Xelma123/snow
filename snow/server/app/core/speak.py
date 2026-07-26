"""Natural Turkish replies for tool results (spoken + written).

Policy-driven phrasing for *offline/rules* paths (no LLM).
LLM path should produce natural text via system prompt; this module
also sanitizes residual technical jargon (on/off/entity_id).
"""

from __future__ import annotations

import re
from typing import Any


def soft_for_speech(text: str) -> str:
    """Strip jargon so TTS never reads raw HA states."""
    t = (text or "").strip()
    if not t:
        return "Tamam."
    # entity ids
    t = re.sub(r"\b(?:light|media_player|switch|scene)\.[a-zA-Z0-9_]+\b", "", t)
    # raw states as whole words
    repl = {
        r"\boff\b": "kapalı",
        r"\bon\b": "açık",
        r"\bplaying\b": "oynatılıyor",
        r"\bpaused\b": "duraklatıldı",
        r"\bidle\b": "boşta",
        r"\bstandby\b": "beklemede",
        r"\btoggle\b": "değiştirildi",
        r"\bstate\b": "durum",
        r"\bbrightness_pct\b": "parlaklık",
        r"\bentity_id\b": "",
    }
    for pat, rep in repl.items():
        t = re.sub(pat, rep, t, flags=re.IGNORECASE)
    t = re.sub(r"\s{2,}", " ", t).strip(" ·,;:")
    # "%80" style → "yüzde 80" for TTS friendliness
    t = re.sub(r"%\s*(\d+)", r"yüzde \1", t)
    t = re.sub(r"(\d+)\s*%", r"yüzde \1", t)
    if len(t) > 200:
        t = t[:197] + "…"
    return t or "Tamam."


def _state_tr(state: str | None) -> str:
    s = (state or "").lower()
    return {
        "on": "açık",
        "off": "kapalı",
        "playing": "oynatılıyor",
        "paused": "duraklatıldı",
        "idle": "boşta",
        "standby": "beklemede",
        "unavailable": "ulaşılamıyor",
        "unknown": "bilinmiyor",
    }.get(s, s or "bilinmiyor")


def humanize_tool_result(tool: str, result: dict[str, Any]) -> str:
    """Map tool JSON → short spoken Turkish (rules / fallback synthesizer)."""
    if not isinstance(result, dict):
        return "Tamam."
    if result.get("error"):
        err = soft_for_speech(str(result["error"]))
        return f"Yapamadım. {err}"

    tool = (tool or "").lower()

    if tool == "profile_set" or (result.get("ok") and result.get("user_name")):
        name = result.get("user_name") or ""
        return f"Tamam, seni {name} olarak hatırlayacağım." if name else "Adını kaydettim."

    if tool == "profile_get" or ("user_name" in result and tool != "profile_set"):
        un = result.get("user_name")
        return f"Adın {un}." if un else "Henüz adını kaydetmedim."

    if tool == "get_weather" or "condition_tr" in result:
        place = result.get("place") or "Ev"
        cond = result.get("condition_tr") or ""
        temp = result.get("temperature_c")
        hum = result.get("humidity_pct")
        parts = [f"{place}de {cond}".strip()]
        if temp is not None:
            parts.append(f"{temp} derece")
        if hum is not None:
            parts.append(f"nem yüzde {hum}")
        return soft_for_speech(", ".join(parts) + ".")

    if tool == "run_routine" or result.get("routine_id"):
        if result.get("ok"):
            title = result.get("title") or result.get("routine_id") or "rutin"
            return f"{title} tamam."
        return "Rutin yarıda kaldı."

    if tool == "list_jobs" or isinstance(result.get("jobs"), list):
        jobs = result.get("jobs") or []
        if not jobs:
            return "Bekleyen zamanlanmış iş yok."
        n = len(jobs)
        first = jobs[0]
        label = first.get("label") or "iş"
        sec = first.get("in_seconds")
        if n == 1 and sec is not None:
            return f"Bir iş var: {label}, yaklaşık {sec} saniye sonra."
        return f"{n} bekleyen işin var. İlki: {label}."

    if tool == "cancel_job":
        return "Zamanlanmış işi iptal ettim." if result.get("ok") else "O işi iptal edemedim."

    if tool == "list_routines" or result.get("routines"):
        return "Rutinleri listede görebilirsin."

    if tool in ("list_entities", "list_scenes") or "entities" in result or "scenes" in result:
        ents = result.get("entities") or result.get("scenes") or []
        if not ents:
            return "Bu tipte bir şey bulamadım."
        names = [
            str(e.get("name") or e.get("entity_id") or "").split(".")[-1]
            for e in ents[:5]
            if isinstance(e, dict)
        ]
        names = [n for n in names if n]
        return "Buldum: " + ", ".join(names) + "."

    if tool == "activate_scene":
        return "Sahneyi çalıştırdım."

    # Light / media / generic state
    eid = str(result.get("entity_id") or "")
    st = (result.get("state") or "").lower()
    pct = result.get("brightness_pct")

    if tool == "media_control" or eid.startswith("media_player"):
        if st in ("on", "playing"):
            title = result.get("media_title")
            if title:
                return f"Televizyon açık. Şu an: {title}."
            return "Televizyonu açtım." if tool == "media_control" else "Televizyon açık."
        if st in ("off", "standby", "idle"):
            return "Televizyonu kapattım." if tool == "media_control" else "Televizyon kapalı."
        if st == "paused":
            return "Duraklattım."
        return f"Televizyon {_state_tr(st)}."

    if tool in ("light_control", "get_home_state") or eid.startswith("light.") or pct is not None:
        if st == "on" and pct is not None:
            return f"Işık açık, parlaklık yüzde {int(pct)}."
        if st == "on":
            return "Işığı açtım." if tool == "light_control" else "Işık açık."
        if st == "off":
            return "Işığı kapattım." if tool == "light_control" else "Işık kapalı."
        if pct is not None:
            return f"Parlaklığı yüzde {int(pct)} yaptım."
        return "Işıkla ilgili işlemi yaptım."

    if tool == "switch_control":
        if st == "on":
            return "Açtım."
        if st == "off":
            return "Kapattım."
        return "Anahtarı değiştirdim."

    if tool == "pc_control" or result.get("pc_id") or result.get("action") in (
        "wake",
        "sleep",
        "shutdown",
        "reboot",
        "status",
        "lock",
        "close_tab",
        "open_url",
        "open_app",
        "run_macro",
        "volume",
        "mute",
        "unmute",
    ):
        title = str(result.get("title") or result.get("pc_id") or "bilgisayar")
        act = str(result.get("action") or "").lower()
        if act == "wake" or st == "waking":
            return f"{title} için uyandırma sinyali gönderdim."
        if act == "status":
            if result.get("online") or st == "on":
                if result.get("agent_ok"):
                    return f"{title} açık ve ajan hazır."
                return f"{title} ağda görünüyor, açık gibi."
            return f"{title} kapalı veya uykuda görünüyor."
        if act == "sleep":
            return f"{title} uykuya alındı."
        if act == "shutdown":
            return f"{title} kapatılıyor."
        if act == "reboot":
            return f"{title} yeniden başlatılıyor."
        if act == "lock":
            return f"{title} kilitlendi."
        if act == "close_tab":
            return "Aktif sekme kapatma komutunu gönderdim."
        if act == "open_url":
            return "Bağlantıyı bilgisayarda açtım."
        if act == "open_app":
            return "Uygulamayı açmayı denedim."
        if act == "run_macro":
            mid = result.get("macro_id") or ""
            return f"Bilgisayar makrosu çalıştı{': ' + str(mid) if mid else ''}."
        if act in ("volume", "mute", "unmute"):
            return "Ses ayarını güncelledim."
        if result.get("ok"):
            return f"{title} için işlemi yaptım."
        return f"{title} ile ilgili işlem tamam."

    if result.get("default_light") or result.get("default_tv"):
        bits = []
        dl = result.get("default_light") or {}
        if dl:
            bits.append(
                f"Işık {_state_tr(dl.get('state'))}"
                + (
                    f", yüzde {int(dl['brightness_pct'])}"
                    if dl.get("brightness_pct") is not None
                    else ""
                )
            )
        tv = result.get("default_tv") or {}
        if tv:
            bits.append(f"TV {_state_tr(tv.get('state'))}")
        return soft_for_speech(". ".join(bits) + ".") if bits else "Ev durumunu aldım."

    if result.get("ok") is True:
        return "Tamam, hallettim."

    return "Tamam."


def humanize_actions(actions: list) -> str | None:
    """Synthesize from last tool action in a batch."""
    if not actions:
        return None
    last = actions[-1]
    tool = str(last.get("tool") or "")
    raw = last.get("result") or "{}"
    try:
        data = raw if isinstance(raw, dict) else __import__("json").loads(raw or "{}")
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(data, dict):
        return None
    return humanize_tool_result(tool, data)
