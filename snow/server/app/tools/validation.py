"""Server-side tool argument validation (structured-output skill).

Free OpenRouter models may emit incomplete tool JSON; never trust args
before HA mutation.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator


class ValidationFail(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class GetHomeStateArgs(BaseModel):
    entity_id: str | None = Field(default=None, description="light.* or alias")


class LightControlArgs(BaseModel):
    entity_id: str | None = None
    action: Literal["on", "off", "toggle"]
    brightness_abs: int | None = Field(default=None, ge=0, le=255)
    brightness_delta: int | None = Field(default=None, ge=-255, le=255)
    color_temp_kelvin: int | None = Field(default=None, ge=1500, le=6500)
    rgb_color: list[int] | None = None

    @field_validator("rgb_color")
    @classmethod
    def _rgb(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return v
        if len(v) != 3:
            raise ValueError("rgb_color must be 3 ints")
        for c in v:
            if not 0 <= int(c) <= 255:
                raise ValueError("rgb channel 0-255")
        return [int(c) for c in v]


class SwitchControlArgs(BaseModel):
    entity_id: str
    action: Literal["on", "off", "toggle"]


class MediaControlArgs(BaseModel):
    entity_id: str | None = None
    action: Literal[
        "on",
        "off",
        "toggle",
        "play",
        "pause",
        "stop",
        "play_pause",
        "next",
        "previous",
        "volume_up",
        "volume_down",
        "mute",
        "volume_set",
    ]
    volume_level: float | None = Field(default=None, ge=0.0, le=1.0)


class ListEntitiesArgs(BaseModel):
    domain: Literal["light", "switch", "scene", "media_player"] = "light"


class EmptyArgs(BaseModel):
    pass


class ActivateSceneArgs(BaseModel):
    entity_id: str


class WeatherArgs(BaseModel):
    place: str | None = None


class ProfileGetArgs(BaseModel):
    key: str | None = "user_name"


class ProfileSetArgs(BaseModel):
    user_name: str = Field(min_length=1, max_length=48)


class RunRoutineArgs(BaseModel):
    routine_id: str = Field(min_length=1, max_length=64)


class CancelJobArgs(BaseModel):
    job_id: int = Field(ge=1)


class AnswerOnlyArgs(BaseModel):
    note: str | None = None


class PcControlArgs(BaseModel):
    """One-shot PC actions only — no recurring schedules."""

    target: str | None = Field(
        default=None, description="PC id or alias (msi, bilgisayar); empty=default"
    )
    action: Literal[
        "status",
        "wake",
        "sleep",
        "shutdown",
        "reboot",
        "lock",
        "volume",
        "mute",
        "unmute",
        "open_url",
        "close_tab",
        "open_app",
        "run_macro",
    ]
    value: str | int | float | None = Field(
        default=None,
        description="volume 0-100, open_url URL, open_app id, run_macro id",
    )


_MODELS: dict[str, type[BaseModel]] = {
    "get_home_state": GetHomeStateArgs,
    "light_control": LightControlArgs,
    "switch_control": SwitchControlArgs,
    "media_control": MediaControlArgs,
    "list_entities": ListEntitiesArgs,
    "list_scenes": EmptyArgs,
    "activate_scene": ActivateSceneArgs,
    "home_summary": EmptyArgs,
    "get_weather": WeatherArgs,
    "profile_get": ProfileGetArgs,
    "profile_set": ProfileSetArgs,
    "run_routine": RunRoutineArgs,
    "list_routines": EmptyArgs,
    "list_jobs": EmptyArgs,
    "cancel_job": CancelJobArgs,
    "answer_only": AnswerOnlyArgs,
    "pc_control": PcControlArgs,
}


def validate_tool_args(name: str, args: dict[str, Any] | None) -> dict[str, Any]:
    """Return cleaned args or raise ValidationFail."""
    model = _MODELS.get(name)
    if model is None:
        # Unknown tools: pass through empty only
        if args:
            raise ValidationFail(f"Bilinmeyen araç: {name}")
        return {}
    raw = args if isinstance(args, dict) else {}
    try:
        obj = model.model_validate(raw)
        return obj.model_dump(exclude_none=True)
    except ValidationError as e:
        # Compact Turkish-friendly message
        parts = []
        for err in e.errors()[:4]:
            loc = ".".join(str(x) for x in err.get("loc") or ())
            parts.append(f"{loc}: {err.get('msg')}")
        raise ValidationFail("; ".join(parts) or "Geçersiz araç argümanları") from e
