"""Tool handlers — one module per domain. Dispatch table built in executor."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.tools.context import ToolContext
from app.tools.handlers import home, jobs, light, media, pc, profile, routines, weather

Handler = Callable[[ToolContext, dict[str, Any]], Awaitable[Any]]

HANDLERS: dict[str, Handler] = {
    "get_home_state": light.get_home_state,
    "light_control": light.light_control,
    "switch_control": light.switch_control,
    "media_control": media.media_control,
    "list_entities": home.list_entities,
    "list_scenes": home.list_scenes,
    "activate_scene": home.activate_scene,
    "home_summary": home.home_summary,
    "get_weather": weather.get_weather,
    "profile_get": profile.profile_get,
    "profile_set": profile.profile_set,
    "run_routine": routines.run_routine,
    "list_routines": routines.list_routines,
    "list_jobs": jobs.list_jobs,
    "cancel_job": jobs.cancel_job,
    "answer_only": home.answer_only,
    "pc_control": pc.pc_control,
}

__all__ = ["HANDLERS", "Handler"]
