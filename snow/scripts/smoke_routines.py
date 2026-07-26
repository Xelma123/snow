"""Load personal/routines.yaml and verify film_gecesi steps."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from app.config import Settings  # noqa: E402
from app.tools.routines import get_routine, list_routine_summaries  # noqa: E402


def main() -> int:
    settings = Settings(
        devices_file=str(ROOT / "personal" / "devices.yaml"),
        data_dir=str(ROOT / "data"),
    )
    summaries = list_routine_summaries(settings)
    ids = {r["id"] for r in summaries}
    assert "film_gecesi" in ids, f"film_gecesi missing: {ids}"
    assert "iyi_geceler" in ids

    film = get_routine(settings, "film_gecesi")
    assert film is not None
    steps = film.get("steps") or []
    assert len(steps) >= 2, steps
    tools = [st.get("tool") for st in steps if isinstance(st, dict)]
    assert "light_control" in tools
    assert "media_control" in tools

    by_alias = get_routine(settings, "film")
    assert by_alias and by_alias.get("id") == "film_gecesi"

    print(f"OK routines: {sorted(ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
