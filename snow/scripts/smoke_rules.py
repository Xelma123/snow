"""Offline smoke tests for fold/split/delay (no HA required)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from app.core.device_rules import _fold, _parse_delay_seconds, split_intents  # noqa: E402


def main() -> None:
    assert "isik" in _fold("Işığı aç") or "isigi" in _fold("Işığı aç")
    assert split_intents("ışığı aç ve tv kapat") == ["ışığı aç", "tv kapat"]
    assert _parse_delay_seconds(_fold("5 dakika sonra kapat")) == 300
    assert _parse_delay_seconds(_fold("10 dk sonra ışığı kapat")) == 600
    print("smoke_rules: OK")


if __name__ == "__main__":
    main()
