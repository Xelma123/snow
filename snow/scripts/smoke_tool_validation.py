"""Tool arg validation — invalid payloads must fail before HA."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from app.tools.validation import ValidationFail, validate_tool_args  # noqa: E402


def main() -> int:
    ok = validate_tool_args("light_control", {"action": "on", "brightness_abs": 100})
    assert ok["action"] == "on"

    try:
        validate_tool_args("light_control", {"action": "explode"})
        raise SystemExit("should have failed bad action")
    except ValidationFail:
        pass

    try:
        validate_tool_args("light_control", {"action": "on", "brightness_abs": 9999})
        raise SystemExit("should have failed brightness")
    except ValidationFail:
        pass

    try:
        validate_tool_args("cancel_job", {"job_id": 0})
        raise SystemExit("should have failed job_id")
    except ValidationFail:
        pass

    c = validate_tool_args("cancel_job", {"job_id": 3})
    assert c["job_id"] == 3

    print("OK tool validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
