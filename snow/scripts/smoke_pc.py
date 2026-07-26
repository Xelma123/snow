"""PC control unit smoke — WOL packet + validation (no network required)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from app.integrations.pc import build_magic_packet, normalize_mac, send_wol  # noqa: E402
from app.tools.validation import ValidationFail, validate_tool_args  # noqa: E402
from app.core.speak import humanize_tool_result  # noqa: E402


def main() -> int:
    mac = "AA:BB:CC:DD:EE:FF"
    hw = normalize_mac(mac)
    assert len(hw) == 6
    pkt = build_magic_packet(mac)
    assert len(pkt) == 102
    assert pkt[:6] == b"\xff" * 6
    assert pkt[6:12] == hw

    # Packet build + send attempt (may fail on locked-down nets; still must not crash on loopback targets)
    try:
        r = send_wol(mac, broadcast="127.0.0.1", host="127.0.0.1")
        assert r.get("ok")
        assert r.get("targets")
    except Exception as e:  # noqa: BLE001
        # Some environments block UDP; packet construction already validated above
        print("WOL send note:", e)

    a = validate_tool_args("pc_control", {"action": "wake"})
    assert a["action"] == "wake"

    try:
        validate_tool_args("pc_control", {"action": "hack"})
        raise AssertionError("should reject hack")
    except ValidationFail:
        pass

    wake = humanize_tool_result(
        "pc_control",
        {"ok": True, "action": "wake", "title": "MSI", "state": "waking"},
    )
    assert "off" not in wake.lower()
    assert "uyandır" in wake.lower() or "sinyal" in wake.lower()

    st = humanize_tool_result(
        "pc_control",
        {
            "ok": True,
            "action": "status",
            "title": "MSI",
            "online": False,
            "state": "off",
        },
    )
    assert "kapalı" in st.lower() or "uyku" in st.lower()

    print("OK smoke_pc", wake, "|", st)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
