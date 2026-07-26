"""Identity classifier — QUERY vs SET must never confuse 'adım ne' with a name."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from app.core.identity import IdentityKind, classify_identity, validate_display_name


def main() -> None:
    for q in (
        "adım ne",
        "benim adım ne",
        "selam adım ne",
        "ismim nedir",
        "adımı söyle",
        "beni tanıyor musun",
        "benim adım ne?",
    ):
        i = classify_identity(q)
        assert i is not None and i.kind == IdentityKind.QUERY, (q, i)

    for s, exp in (
        ("benim adım murat", "Murat"),
        ("adım Murat", "Murat"),
        ("ismim Ayşe", "Ayşe"),
        ("adımı Murat olarak kaydet", "Murat"),
    ):
        i = classify_identity(s)
        assert i and i.kind == IdentityKind.SET and i.name == exp, (s, i)

    assert validate_display_name("ne") is None
    assert validate_display_name("kim") is None
    assert validate_display_name("Murat") == "Murat"
    assert classify_identity("selam nasılsın") is None
    assert classify_identity("ışığı aç") is None
    print("smoke_identity: OK")


if __name__ == "__main__":
    main()
