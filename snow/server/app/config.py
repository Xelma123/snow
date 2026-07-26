"""Snow configuration — single OpenRouter model, personal-friendly defaults."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Locked model — no UI picker.
# 20B free: more reliable quota for daily chat; 120B free often rate-limits.
OPENROUTER_MODEL = "openai/gpt-oss-20b:free"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = REPO_ROOT / "data"
DEFAULT_DEVICES_FILE = REPO_ROOT / "personal" / "devices.yaml"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    snow_app_token: str = "change-me"
    openrouter_api_key: str = ""
    ha_url: str = "http://192.168.1.10:8123"
    ha_token: str = ""
    ha_default_light: str = "light.bulb"
    ha_default_tv: str = "media_player.arcelik_android_tv"
    home_lat: float = 41.0082
    home_lon: float = 28.9784
    snow_host: str = "0.0.0.0"
    snow_port: int = 8787
    session_max_messages: int = 24
    data_dir: str = str(DEFAULT_DATA_DIR)
    devices_file: str = str(DEFAULT_DEVICES_FILE)
    pcs_file: str = str(REPO_ROOT / "personal" / "pcs.yaml")
    snow_pc_agent_token: str = ""
    rate_limit_per_minute: int = 60
    enable_rule_fallback: bool = True

    @property
    def db_path(self) -> Path:
        return Path(self.data_dir) / "snow.db"

    @property
    def weak_token(self) -> bool:
        return self.snow_app_token in ("", "change-me", "change-me-to-a-long-random-string")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def validate_settings(settings: Settings) -> list[str]:
    warnings: list[str] = []
    if settings.weak_token:
        warnings.append("SNOW_APP_TOKEN varsayılan/zayıf — mutlaka değiştir.")
    if not settings.openrouter_api_key:
        warnings.append("OPENROUTER_API_KEY boş — AI sohbet çalışmaz (kural fallback olabilir).")
    if not settings.ha_token:
        warnings.append("HA_TOKEN boş — ev kontrolü çalışmaz.")
    if not settings.ha_url:
        warnings.append("HA_URL boş.")
    return warnings
