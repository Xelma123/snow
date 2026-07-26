"""Natural speech helpers — no raw on/off for users."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from app.core.speak import humanize_tool_result, soft_for_speech  # noqa: E402


def main() -> int:
    on = humanize_tool_result(
        "light_control",
        {"entity_id": "light.bulb", "state": "on", "brightness_pct": 80},
    )
    assert "off" not in on.lower()
    assert "on" not in on.split()  # no bare english on
    assert "aç" in on.lower() or "parlak" in on.lower() or "yüzde" in on.lower()

    off = humanize_tool_result(
        "light_control", {"entity_id": "light.bulb", "state": "off"}
    )
    assert "off" not in off.lower()
    assert "kapat" in off.lower()

    soft = soft_for_speech("Işık off, brightness_pct 50")
    assert "off" not in soft.lower()
    assert "brightness" not in soft.lower()

    print("OK speak", on, "|", off)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
