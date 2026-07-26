"""Profile display-name validator — blocklist and acceptance."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from app.core.identity import validate_display_name  # noqa: E402


def main() -> int:
    for bad in ("ne", "kim", "nedir", "adım", "isim", "x", "a", "123", ""):
        assert validate_display_name(bad) is None, bad

    for good, exp in (
        ("Murat", "Murat"),
        ("murat", "Murat"),
        ("Ayşe", "Ayşe"),
        ("  Elif  ", "Elif"),
    ):
        got = validate_display_name(good)
        assert got == exp, (good, got, exp)

    print("OK profile validator")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
