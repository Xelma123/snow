"""Tool bus metadata — risk, mutate, domain. Schemas live in schemas.py."""

from __future__ import annotations

from typing import Any, TypedDict


class ToolMeta(TypedDict, total=False):
    name: str
    risk: str  # low | medium | high
    mutate: bool
    domains: list[str]
    description: str


# Canonical registry of what Snow can do. Add tools here + handler in executor.
TOOL_META: dict[str, ToolMeta] = {
    "get_home_state": {
        "name": "get_home_state",
        "risk": "low",
        "mutate": False,
        "domains": ["light"],
    },
    "light_control": {
        "name": "light_control",
        "risk": "low",
        "mutate": True,
        "domains": ["light"],
    },
    "switch_control": {
        "name": "switch_control",
        "risk": "low",
        "mutate": True,
        "domains": ["switch"],
    },
    "media_control": {
        "name": "media_control",
        "risk": "low",
        "mutate": True,
        "domains": ["media_player"],
    },
    "list_entities": {
        "name": "list_entities",
        "risk": "low",
        "mutate": False,
        "domains": ["*"],
    },
    "list_scenes": {
        "name": "list_scenes",
        "risk": "low",
        "mutate": False,
        "domains": ["scene"],
    },
    "activate_scene": {
        "name": "activate_scene",
        "risk": "low",
        "mutate": True,
        "domains": ["scene"],
    },
    "home_summary": {
        "name": "home_summary",
        "risk": "low",
        "mutate": False,
        "domains": ["*"],
    },
    "get_weather": {
        "name": "get_weather",
        "risk": "low",
        "mutate": False,
        "domains": [],
    },
    "profile_get": {
        "name": "profile_get",
        "risk": "low",
        "mutate": False,
        "domains": [],
    },
    "profile_set": {
        "name": "profile_set",
        "risk": "low",
        "mutate": True,
        "domains": [],
    },
    "run_routine": {
        "name": "run_routine",
        "risk": "low",
        "mutate": True,
        "domains": ["*"],
        "description": "Named multi-step home macros from personal/routines.yaml",
    },
    "list_routines": {
        "name": "list_routines",
        "risk": "low",
        "mutate": False,
        "domains": [],
    },
    "list_jobs": {
        "name": "list_jobs",
        "risk": "low",
        "mutate": False,
        "domains": [],
    },
    "cancel_job": {
        "name": "cancel_job",
        "risk": "low",
        "mutate": True,
        "domains": [],
    },
    "answer_only": {
        "name": "answer_only",
        "risk": "low",
        "mutate": False,
        "domains": [],
    },
    "pc_control": {
        "name": "pc_control",
        "risk": "medium",
        "mutate": True,
        "domains": ["pc"],
        "description": "MSI/PC: wake (WOL), status, sleep/shutdown/reboot, lock, desktop",
    },
}


def mutate_tools() -> set[str]:
    return {n for n, m in TOOL_META.items() if m.get("mutate")}


def tool_names() -> list[str]:
    return list(TOOL_META.keys())


# Tools that change HA entity state → world inventory cache must drop.
_HOME_MUTATE_DOMAINS = {"light", "switch", "media_player", "scene", "*"}


def is_home_mutating(name: str) -> bool:
    """True if tool may change live HA inventory (not profile/jobs alone)."""
    meta = TOOL_META.get(name)
    if not meta or not meta.get("mutate"):
        return False
    domains = set(meta.get("domains") or [])
    if not domains:
        return False
    return bool(domains & _HOME_MUTATE_DOMAINS)


def assert_schema_alignment(schema_names: list[str]) -> None:
    """Raise AssertionError if OpenRouter schemas drift from TOOL_META."""
    meta = set(TOOL_META.keys())
    schemas = set(schema_names)
    missing_meta = schemas - meta
    missing_schema = meta - schemas
    if missing_meta or missing_schema:
        raise AssertionError(
            f"tool bus drift: schema-only={sorted(missing_meta)} "
            f"meta-only={sorted(missing_schema)}"
        )
