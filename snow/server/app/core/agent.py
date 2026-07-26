"""
Snow dynamic agent core.

Pipeline (Jarvis-style, not regex spaghetti):
  1) Persist user message
  2) Identity path  → profile tools only (validated SET / QUERY)
  3) Device fast-path → high-confidence light/TV/delay rules (actuators only)
  4) Multi-intent device split when all segments are device-confident
  5) Default: LLM + tools + LIVE home inventory every turn
  6) Offline device rules if OpenRouter fails

Side effects (name write, HA call) always go through tools/storage validators.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import OPENROUTER_MODEL, Settings, get_settings
from app.core.context import build_world_context, format_world_for_prompt, invalidate_home_cache
from app.core.device_rules import split_intents, try_rule_fallback
from app.core.identity import IdentityKind, classify_identity
from app.core.openrouter import OpenRouterError, chat_completion
from app.core.prompts import build_system_prompt
from app.core.speak import humanize_actions, humanize_tool_result, soft_for_speech
from app.integrations.ha import HomeAssistant
from app.storage import audit as audit_store
from app.storage import profile as profile_store
from app.storage import sessions as session_store
from app.tools.manifest import is_home_mutating
from app.tools.registry import ToolExecutor, openrouter_tools_schema

logger = logging.getLogger("snow.agent")
MAX_TOOL_ROUNDS = 8


def _ok(
    sid: str,
    reply: str,
    *,
    actions: list | None = None,
    model: str = OPENROUTER_MODEL,
    error: str | None = None,
    fallback: bool = False,
    home_snapshot: dict | None = None,
    path: str = "llm",
) -> dict[str, Any]:
    return {
        "session_id": sid,
        "reply": soft_for_speech(reply),
        "actions": actions or [],
        "model": model,
        "error": error,
        "fallback": fallback,
        "home_snapshot": home_snapshot,
        "path": path,
    }


async def handle_chat(
    user_text: str,
    session_id: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    text = (user_text or "").strip()

    try:
        sid = await session_store.ensure_session(settings, session_id)
    except Exception as e:  # noqa: BLE001
        logger.exception("session ensure failed")
        return _ok("local", f"Oturum açılamadı: {e}", error=str(e), path="error")

    if not text:
        return _ok(sid, "Bir komut yaz veya sesle söyle.", path="empty")

    try:
        await session_store.append_message(settings, sid, "user", text)
    except Exception:  # noqa: BLE001
        logger.exception("append user failed")

    # --- Path A: Identity (deterministic, validated) ---
    try:
        ident = classify_identity(text)
        if ident is not None:
            result = await _identity_path(settings, sid, ident)
            if result:
                return result
    except Exception:  # noqa: BLE001
        logger.exception("identity path failed — continuing")

    # --- Path B: Multi device intents (all must be device-confident) ---
    segments = split_intents(text)
    if len(segments) > 1:
        multi = await _device_multi(settings, sid, segments)
        if multi is not None:
            return multi

    # --- Path C: Single high-confidence device/delay rule ---
    # Only actuator-like; identity is NOT handled here anymore.
    try:
        fb = await try_rule_fallback(settings, text)
        if fb and _is_device_or_schedule(fb):
            reply, actions = await _enrich_tool_results(fb)
            await _persist_actions(settings, sid, actions)
            await _save_assistant(settings, sid, reply)
            if _mutated_home(actions):
                invalidate_home_cache()
            return _ok(
                sid,
                reply,
                actions=actions,
                model="device-rules",
                fallback=True,
                home_snapshot=await _safe_snapshot(settings),
                path="device-rules",
            )
    except Exception:  # noqa: BLE001
        logger.exception("device rules failed")

    # --- Path D: Dynamic LLM + tools + live inventory ---
    try:
        return await _llm_loop(settings, sid, text)
    except OpenRouterError as e:
        logger.warning("openrouter down: %s", e)
        detail = str(e)
        # User-facing: keep short; free models often 429 / empty key
        if "eksik" in detail.lower() or "api_key" in detail.lower():
            tip = "Sunucuda OPENROUTER_API_KEY eksik görünüyor."
        elif "429" in detail or "rate" in detail.lower():
            tip = "Ücretsiz model kotası dolmuş olabilir; biraz sonra dene."
        elif "401" in detail or "403" in detail:
            tip = "OpenRouter anahtarı geçersiz olabilir."
        else:
            tip = "OpenRouter’a ulaşılamadı (ağ veya model)."
        return _ok(
            sid,
            f"Şu an sohbet AI’sı kapalı ({tip}) "
            "Işık/TV için net komutlar hâlâ çalışır: "
            "'ışığı aç', 'tv kapat', '5 dk sonra ışığı kapat'.",
            error=detail,
            home_snapshot=await _safe_snapshot(settings),
            path="offline",
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("llm loop failed")
        return _ok(
            sid,
            f"İşlenemedi: {e}",
            error=str(e),
            home_snapshot=await _safe_snapshot(settings),
            path="error",
        )


def _is_device_or_schedule(fb: dict[str, Any]) -> bool:
    """Reject non-device rule hits from ever looking like identity hacks."""
    actions = fb.get("actions") or []
    if not actions and fb.get("reply"):
        # pure reply without tools — only allow if explicitly device-rules scheduled ok
        return False
    for a in actions:
        tool = (a.get("tool") or "").lower()
        if tool in {
            "light_control",
            "get_home_state",
            "media_control",
            "switch_control",
            "activate_scene",
            "home_summary",
            "get_weather",
            "list_entities",
            "list_scenes",
            "schedule",
            "run_routine",
            "list_routines",
            "list_jobs",
            "cancel_job",
        }:
            return True
        if tool.startswith("profile"):
            return False
    # schedule replies
    if (fb.get("reply") or "").startswith("Tamam —") and "sonra" in (fb.get("reply") or ""):
        return True
    return bool(actions)


def _mutated_home(actions: list) -> bool:
    return any(is_home_mutating(a.get("tool") or "") for a in actions)


async def _identity_path(
    settings: Settings, sid: str, ident
) -> dict[str, Any] | None:
    tools = ToolExecutor(settings, HomeAssistant(settings))
    if ident.kind == IdentityKind.QUERY:
        raw = await tools.run("profile_get", {"key": "user_name"})
        data = json.loads(raw)
        uname = data.get("user_name")
        reply = (
            f"Adın {uname}."
            if uname
            else "Henüz adını kaydetmedim. 'Benim adım Murat' dersen kalıcı yazarım."
        )
        actions = [
            {"tool": "profile_get", "arguments": '{"key":"user_name"}', "result": raw}
        ]
        await _persist_actions(settings, sid, actions)
        await _save_assistant(settings, sid, reply)
        return _ok(
            sid,
            reply,
            actions=actions,
            model="identity",
            path="identity-query",
        )

    if ident.kind == IdentityKind.SET and ident.name:
        raw = await tools.run("profile_set", {"user_name": ident.name})
        data = json.loads(raw)
        if data.get("error"):
            reply = data["error"]
        else:
            reply = f"Tamam, seni {data.get('user_name', ident.name)} olarak hatırlayacağım."
        actions = [
            {
                "tool": "profile_set",
                "arguments": json.dumps({"user_name": ident.name}, ensure_ascii=False),
                "result": raw,
            }
        ]
        await _persist_actions(settings, sid, actions)
        await _save_assistant(settings, sid, reply)
        return _ok(
            sid,
            reply,
            actions=actions,
            model="identity",
            path="identity-set",
        )
    return None


async def _device_multi(
    settings: Settings, sid: str, segments: list[str]
) -> dict[str, Any] | None:
    replies: list[str] = []
    actions: list[dict[str, Any]] = []
    for seg in segments:
        # Never run identity-confused multi on chat segments
        if classify_identity(seg) is not None:
            return None
        try:
            fb = await try_rule_fallback(settings, seg)
        except Exception:  # noqa: BLE001
            fb = None
        if not fb or not _is_device_or_schedule(fb):
            return None
        reply, acts = await _enrich_tool_results(fb)
        replies.append(reply)
        actions.extend(acts)
    await _persist_actions(settings, sid, actions)
    final = " ".join(replies)
    await _save_assistant(settings, sid, final)
    if _mutated_home(actions):
        invalidate_home_cache()
    return _ok(
        sid,
        final,
        actions=actions,
        model="device-multi",
        fallback=True,
        home_snapshot=await _safe_snapshot(settings),
        path="device-multi",
    )


async def _save_assistant(settings: Settings, sid: str, reply: str) -> None:
    try:
        await session_store.append_message(settings, sid, "assistant", reply)
    except Exception:  # noqa: BLE001
        logger.exception("append assistant failed")


async def _enrich_tool_results(fb: dict[str, Any]) -> tuple[str, list]:
    """Natural TR from tools (rules path / empty LLM). Never expose raw HA states."""
    actions = list(fb.get("actions") or [])
    seed = str(fb.get("reply") or "").strip()
    # Prefer structured humanize from last tool
    spoken = humanize_actions(actions)
    if spoken:
        return soft_for_speech(spoken), actions
    if seed:
        return soft_for_speech(seed), actions
    return "Tamam.", actions


async def _persist_actions(settings: Settings, sid: str, actions: list) -> None:
    for a in actions:
        try:
            await audit_store.log_tool(
                settings,
                sid,
                a.get("tool", "?"),
                str(a.get("arguments", "")),
                str(a.get("result", "")),
            )
        except Exception:  # noqa: BLE001
            logger.exception("audit log failed")


async def _safe_snapshot(settings: Settings) -> dict[str, Any] | None:
    try:
        return await HomeAssistant(settings).light_snapshot()
    except Exception:  # noqa: BLE001
        return None


async def _llm_loop(settings: Settings, sid: str, text: str) -> dict[str, Any]:
    """Primary Jarvis path: model + tools + live world context."""
    ha = HomeAssistant(settings)
    tools = ToolExecutor(settings, ha)
    actions: list[dict[str, Any]] = []

    try:
        clean_hist = await session_store.get_history_for_llm(settings, sid)
    except Exception:  # noqa: BLE001
        clean_hist = [{"role": "user", "content": text}]

    world = await build_world_context(settings)
    world_block = format_world_for_prompt(world)
    system = build_system_prompt(settings) + "\n\n" + world_block
    logger.debug(
        "llm context chars system=%s hist_msgs=%s",
        len(system),
        len(clean_hist),
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        *clean_hist,
    ]
    schemas = openrouter_tools_schema()

    for _ in range(MAX_TOOL_ROUNDS):
        data = await chat_completion(settings, messages, tools=schemas)
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        tool_calls = msg.get("tool_calls") or []

        if tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.get("content") or "",
                    "tool_calls": tool_calls,
                }
            )
            for tc in tool_calls:
                fn = tc.get("function") or {}
                name = fn.get("name") or ""
                raw_args = fn.get("arguments") or "{}"
                # Server-side guard: profile_set always validated inside tool
                result_str = await tools.run(name, raw_args)
                # Home inventory cache: ToolExecutor invalidates mutate tools.
                actions.append(
                    {"tool": name, "arguments": raw_args, "result": result_str}
                )
                await _persist_actions(settings, sid, actions[-1:])
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.get("id") or name,
                        "content": result_str,
                    }
                )
            continue

        reply = (msg.get("content") or "").strip()
        if not reply and actions:
            synth, _ = await _enrich_tool_results(
                {"reply": "Tamam.", "actions": actions}
            )
            reply = synth
        if not reply:
            reply = "Anlayamadım; bir kez daha dener misin?"
        # LLM should already be natural; strip residual jargon before voice/UI
        reply = soft_for_speech(reply)

        await _save_assistant(settings, sid, reply)
        return _ok(
            sid,
            reply,
            actions=actions,
            home_snapshot=await _safe_snapshot(settings),
            path="llm",
        )

    return _ok(
        sid,
        "İşlem yarıda kaldı; daha kısa dene.",
        actions=actions,
        home_snapshot=await _safe_snapshot(settings),
        path="llm-truncated",
    )
