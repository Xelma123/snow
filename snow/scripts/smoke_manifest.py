"""Assert tool bus: schemas ↔ manifest ↔ handlers aligned."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from app.tools.handlers import HANDLERS  # noqa: E402
from app.tools.manifest import (  # noqa: E402
    TOOL_META,
    assert_schema_alignment,
    is_home_mutating,
    mutate_tools,
)
from app.tools.schemas import schema_tool_names  # noqa: E402


def main() -> int:
    names = schema_tool_names()
    assert_schema_alignment(names)
    assert set(names) == set(TOOL_META), "schema names != TOOL_META"
    assert set(HANDLERS) == set(TOOL_META), "HANDLERS != TOOL_META"
    assert is_home_mutating("light_control")
    assert is_home_mutating("run_routine")
    assert not is_home_mutating("profile_set")
    assert not is_home_mutating("list_jobs")
    assert "light_control" in mutate_tools()
    print(f"OK manifest: {len(names)} tools aligned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
