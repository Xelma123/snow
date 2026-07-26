"""PC integration — Wake-on-LAN, reachability probe, PC agent HTTP client.

Brain stays on Acer (Snow). Power wake is pure network. Sleep/shutdown/desktop
require the thin agent running on the target Windows machine.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import struct
from pathlib import Path
from typing import Any

import httpx
import yaml

from app.config import Settings
from app.http_client import get_http_client

logger = logging.getLogger("snow.pc")


class PcError(Exception):
    pass


def _pcs_path(settings: Settings) -> Path:
    if getattr(settings, "pcs_file", None):
        p = Path(settings.pcs_file)
        if p.is_file():
            return p
    return Path(settings.devices_file).resolve().parent / "pcs.yaml"


def load_pcs(settings: Settings) -> dict[str, dict[str, Any]]:
    path = _pcs_path(settings)
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    pcs = raw.get("pcs") or raw
    if not isinstance(pcs, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for key, body in pcs.items():
        if isinstance(body, dict):
            out[str(key).lower()] = body
    return out


def resolve_pc(settings: Settings, target: str | None = None) -> tuple[str, dict[str, Any]]:
    pcs = load_pcs(settings)
    if not pcs:
        raise PcError("PC tanımı yok — personal/pcs.yaml ekle.")

    if not target or not str(target).strip():
        # default: first entry
        key = next(iter(pcs))
        return key, pcs[key]

    t = str(target).strip().lower()
    if t in pcs:
        return t, pcs[t]

    for key, body in pcs.items():
        aliases = [key, str(body.get("title") or "").lower()]
        aliases += [str(a).lower() for a in (body.get("aliases") or [])]
        if t in aliases:
            return key, body
        # partial
        for a in aliases:
            if a and (t in a or a in t):
                return key, body

    raise PcError(f"PC bulunamadı: {target}")


def normalize_mac(mac: str) -> bytes:
    cleaned = (
        mac.strip()
        .replace("-", "")
        .replace(":", "")
        .replace(".", "")
        .replace(" ", "")
    )
    if len(cleaned) != 12:
        raise PcError(f"Geçersiz MAC: {mac}")
    try:
        return bytes.fromhex(cleaned)
    except ValueError as e:
        raise PcError(f"Geçersiz MAC: {mac}") from e


def build_magic_packet(mac: str) -> bytes:
    hw = normalize_mac(mac)
    return b"\xff" * 6 + hw * 16


def send_wol(
    mac: str,
    broadcast: str = "255.255.255.255",
    host: str | None = None,
    ports: tuple[int, ...] = (9, 7),
) -> dict[str, Any]:
    """Send magic packet for Ethernet WOL and Wi‑Fi WoWLAN.

    Wi‑Fi wake often needs unicast to the laptop's last IP (not only broadcast).
    We blast broadcast + optional host on UDP 9 and 7.
    """
    packet = build_magic_packet(mac)
    targets: list[str] = []
    for t in (broadcast, "255.255.255.255", (host or "").strip()):
        if t and t not in targets:
            targets.append(t)
    sent: list[str] = []
    errors: list[str] = []
    for addr in targets:
        for port in ports:
            label = f"{addr}:{port}"
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    s.settimeout(2.0)
                    s.sendto(packet, (addr, port))
                    sent.append(label)
            except OSError as e:
                errors.append(f"{label}: {e}")
                logger.warning("WOL send failed to %s: %s", label, e)
    if not sent:
        raise PcError("WOL paketi gönderilemedi: " + "; ".join(errors))
    return {
        "ok": True,
        "action": "wake",
        "mac": mac,
        "host": host,
        "targets": sent,
        "errors": errors or None,
        "note": "Wi-Fi WoWLAN: prefer sleep not full shutdown; enable NIC magic packet",
    }


async def tcp_probe(host: str, port: int, timeout_s: float) -> bool:
    try:
        conn = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(conn, timeout=timeout_s)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:  # noqa: BLE001
            pass
        return True
    except Exception:  # noqa: BLE001
        return False


async def icmp_ping_host(host: str, timeout_s: float) -> bool:
    """Best-effort: try TCP 445/3389/8790 common Windows ports as 'alive' signal.

    True ICMP needs root/raw sockets; multi-port TCP is reliable enough on LAN.
    """
    ports = (8790, 445, 3389, 135, 22)
    timeout_each = max(0.15, min(timeout_s, 1.0) / 2)
    for p in ports:
        if await tcp_probe(host, p, timeout_each):
            return True
    return False


def agent_token(settings: Settings) -> str:
    return (getattr(settings, "snow_pc_agent_token", None) or "").strip()


async def agent_request(
    settings: Settings,
    pc: dict[str, Any],
    method: str,
    path: str,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = str(pc.get("agent_url") or "").rstrip("/")
    if not base:
        raise PcError("agent_url tanımlı değil (pcs.yaml).")
    token = agent_token(settings)
    if not token:
        raise PcError("SNOW_PC_AGENT_TOKEN boş — agent çağrılamaz.")

    url = f"{base}{path}"
    headers = {"Authorization": f"Bearer {token}"}
    client = get_http_client()
    try:
        if method.upper() == "GET":
            r = await client.get(url, headers=headers, timeout=8.0)
        else:
            r = await client.post(url, headers=headers, json=json_body or {}, timeout=12.0)
    except httpx.HTTPError as e:
        raise PcError(f"PC agent'a ulaşılamadı: {e}") from e

    if r.status_code == 401:
        raise PcError("PC agent token reddedildi.")
    if r.status_code >= 400:
        detail = r.text[:200]
        raise PcError(f"PC agent hata {r.status_code}: {detail}")
    try:
        data = r.json()
    except Exception as e:  # noqa: BLE001
        raise PcError("PC agent geçersiz JSON döndü") from e
    if not isinstance(data, dict):
        raise PcError("PC agent beklenmeyen yanıt")
    return data


async def pc_status(settings: Settings, pc: dict[str, Any], pc_id: str) -> dict[str, Any]:
    host = str(pc.get("host") or "").strip()
    if not host:
        raise PcError("host tanımlı değil")
    timeout_ms = int(pc.get("ping_timeout_ms") or 800)
    timeout_s = max(0.2, timeout_ms / 1000.0)

    online = await icmp_ping_host(host, timeout_s)
    agent_ok = False
    agent_detail: dict[str, Any] | None = None
    # Agent health is the strongest signal when the PC is awake
    if str(pc.get("agent_url") or "").strip() and agent_token(settings):
        try:
            agent_detail = await agent_request(settings, pc, "GET", "/health")
            agent_ok = bool(agent_detail.get("ok"))
            if agent_ok:
                online = True
        except PcError:
            agent_detail = None
            agent_ok = False
        except Exception:  # noqa: BLE001
            agent_ok = False

    state = "on" if online else "off"
    return {
        "ok": True,
        "action": "status",
        "pc_id": pc_id,
        "title": pc.get("title") or pc_id,
        "host": host,
        "state": state,
        "online": online,
        "agent_ok": agent_ok,
        "agent": agent_detail,
    }


async def pc_wake(settings: Settings, pc: dict[str, Any], pc_id: str) -> dict[str, Any]:
    mac = str(pc.get("mac") or "").strip()
    if not mac or mac.replace("0", "").replace(":", "").replace("-", "") == "":
        raise PcError("MAC adresi ayarlı değil (personal/pcs.yaml).")
    broadcast = str(pc.get("wol_broadcast") or "255.255.255.255")
    host = str(pc.get("host") or "").strip() or None
    result = await asyncio.to_thread(send_wol, mac, broadcast, host)
    result["pc_id"] = pc_id
    result["title"] = pc.get("title") or pc_id
    result["host"] = host
    result["state"] = "waking"
    return result


async def pc_agent_power(
    settings: Settings, pc: dict[str, Any], pc_id: str, action: str
) -> dict[str, Any]:
    data = await agent_request(
        settings, pc, "POST", "/v1/power", {"action": action}
    )
    return {
        "ok": True,
        "action": action,
        "pc_id": pc_id,
        "title": pc.get("title") or pc_id,
        "state": data.get("state") or action,
        "agent": data,
    }


async def pc_agent_desktop(
    settings: Settings,
    pc: dict[str, Any],
    pc_id: str,
    action: str,
    value: str | int | float | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"action": action}
    if value is not None:
        body["value"] = value
    data = await agent_request(settings, pc, "POST", "/v1/desktop", body)
    return {
        "ok": True,
        "action": action,
        "pc_id": pc_id,
        "title": pc.get("title") or pc_id,
        "value": value,
        "agent": data,
    }


async def pc_agent_macro(
    settings: Settings, pc: dict[str, Any], pc_id: str, macro_id: str
) -> dict[str, Any]:
    data = await agent_request(
        settings, pc, "POST", "/v1/macro", {"id": macro_id}
    )
    return {
        "ok": True,
        "action": "run_macro",
        "pc_id": pc_id,
        "title": pc.get("title") or pc_id,
        "macro_id": macro_id,
        "agent": data,
    }
