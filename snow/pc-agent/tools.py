"""Whitelist desktop/power actions for Windows PC agent.

No free shell. No keylogging. One-shot actions only.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("snow.pc_agent")

# Allowlisted app launchers (id → argv or shell command)
APP_ALLOWLIST: dict[str, list[str]] = {
    "chrome": [r"C:\Program Files\Google\Chrome\Application\chrome.exe"],
    "chrome_x86": [r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"],
    "edge": [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"],
    "firefox": [r"C:\Program Files\Mozilla Firefox\firefox.exe"],
    "notepad": ["notepad.exe"],
    "explorer": ["explorer.exe"],
    "code": [r"C:\Users\{user}\AppData\Local\Programs\Microsoft VS Code\Code.exe"],
    "spotify": [
        r"C:\Users\{user}\AppData\Roaming\Spotify\Spotify.exe",
    ],
}


def _expand(path: str) -> str:
    user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    return path.replace("{user}", user).replace("%USERNAME%", user)


def power_action(action: str) -> dict[str, Any]:
    action = (action or "").lower().strip()
    if action == "lock":
        subprocess.Popen(
            ["rundll32.exe", "user32.dll,LockWorkStation"],
            shell=False,
        )
        return {"ok": True, "action": "lock", "state": "locked"}

    if action == "sleep":
        # Classic Windows sleep (comma is part of rundll32 entry point syntax)
        subprocess.Popen(
            "rundll32.exe powrprof.dll,SetSuspendState 0,1,0",
            shell=True,
        )
        return {"ok": True, "action": "sleep", "state": "sleeping"}

    if action == "shutdown":
        subprocess.Popen(
            ["shutdown", "/s", "/t", "0"],
            shell=False,
        )
        return {"ok": True, "action": "shutdown", "state": "shutting_down"}

    if action == "reboot":
        subprocess.Popen(
            ["shutdown", "/r", "/t", "0"],
            shell=False,
        )
        return {"ok": True, "action": "reboot", "state": "rebooting"}

    return {"ok": False, "error": f"Bilinmeyen power action: {action}"}


def _send_keys_ctrl_w() -> None:
    """Send Ctrl+W to foreground window (close tab / window)."""
    if sys.platform != "win32":
        raise RuntimeError("close_tab yalnızca Windows")
    # Use PowerShell COM SendKeys — no extra deps
    ps = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "[System.Windows.Forms.SendKeys]::SendWait('^w')"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        check=False,
        capture_output=True,
        timeout=10,
    )


def _set_volume(level: int) -> None:
    """Set master volume 0–100 via PowerShell (Windows CoreAudio)."""
    level = max(0, min(100, int(level)))
    # Scalar volume 0.0–1.0
    scalar = level / 100.0
    ps = f"""
$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume {{
  int f(); int g(); int h(); int i();
  int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext);
  int j(); int GetMasterVolumeLevelScalar(out float pfLevel);
}}
[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice {{
  int Activate(ref System.Guid id, int clsCtx, int activationParams, out IAudioEndpointVolume aev);
}}
[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator {{
  int f(); int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice endpoint);
}}
[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class MMDeviceEnumeratorComObject {{ }}
public class Vol {{
  public static void Set(float level) {{
    var enumerator = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
    IMMDevice dev;
    Marshal.ThrowExceptionForHR(enumerator.GetDefaultAudioEndpoint(0, 1, out dev));
    var epGuid = typeof(IAudioEndpointVolume).GUID;
    IAudioEndpointVolume vol;
    Marshal.ThrowExceptionForHR(dev.Activate(ref epGuid, 1, 0, out vol));
    Marshal.ThrowExceptionForHR(vol.SetMasterVolumeLevelScalar(level, System.Guid.Empty));
  }}
}}
'@
[Vol]::Set({scalar})
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        check=False,
        capture_output=True,
        timeout=15,
    )


def desktop_action(action: str, value: Any = None) -> dict[str, Any]:
    action = (action or "").lower().strip()

    if action == "lock":
        return power_action("lock")

    if action == "close_tab":
        _send_keys_ctrl_w()
        return {"ok": True, "action": "close_tab"}

    if action == "open_url":
        url = str(value or "").strip()
        if not url:
            return {"ok": False, "error": "URL gerekli"}
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "https://" + url
        webbrowser.open(url)
        return {"ok": True, "action": "open_url", "value": url}

    if action == "open_app":
        app_id = str(value or "").strip().lower()
        if not app_id:
            return {"ok": False, "error": "app id gerekli"}
        candidates = []
        if app_id in APP_ALLOWLIST:
            candidates = [APP_ALLOWLIST[app_id]]
        elif app_id == "chrome":
            candidates = [APP_ALLOWLIST["chrome"], APP_ALLOWLIST["chrome_x86"]]
        else:
            return {
                "ok": False,
                "error": f"Uygulama allowlist'te yok: {app_id}",
                "allowed": list(APP_ALLOWLIST.keys()),
            }
        for argv in candidates:
            exe = _expand(argv[0])
            if Path(exe).is_file() or exe.endswith(".exe") and "\\" not in exe:
                try:
                    subprocess.Popen([exe] + list(argv[1:]), shell=False)
                    return {"ok": True, "action": "open_app", "value": app_id}
                except OSError as e:
                    logger.warning("open_app %s failed: %s", exe, e)
        return {"ok": False, "error": f"Uygulama bulunamadı: {app_id}"}

    if action == "volume":
        try:
            level = int(value)
        except (TypeError, ValueError):
            return {"ok": False, "error": "volume 0-100 sayı"}
        _set_volume(level)
        return {"ok": True, "action": "volume", "value": level}

    if action == "mute":
        # Toggle mute via nircmd-free: set volume 0
        _set_volume(0)
        return {"ok": True, "action": "mute"}

    if action == "unmute":
        _set_volume(40)
        return {"ok": True, "action": "unmute", "value": 40}

    return {"ok": False, "error": f"Bilinmeyen desktop action: {action}"}


def load_macros(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    macros = raw.get("macros") or raw
    return macros if isinstance(macros, dict) else {}


def run_macro(macro_id: str, macros_path: Path) -> dict[str, Any]:
    macros = load_macros(macros_path)
    mid = (macro_id or "").strip().lower()
    body = macros.get(mid)
    if not body and mid:
        for k, v in macros.items():
            if str(k).lower() == mid:
                body = v
                mid = str(k)
                break
    if not isinstance(body, dict):
        return {
            "ok": False,
            "error": f"Makro yok: {macro_id}",
            "available": list(macros.keys()),
        }
    results = []
    for step in body.get("steps") or []:
        if not isinstance(step, dict):
            continue
        act = str(step.get("action") or "")
        val = step.get("value")
        if act in ("sleep", "shutdown", "reboot", "lock"):
            r = power_action(act)
        else:
            r = desktop_action(act, val)
        results.append(r)
        if not r.get("ok"):
            return {"ok": False, "macro_id": mid, "steps": results}
    return {"ok": True, "macro_id": mid, "steps": results}


def manifest() -> dict[str, Any]:
    return {
        "power": ["sleep", "shutdown", "reboot", "lock"],
        "desktop": [
            "lock",
            "close_tab",
            "open_url",
            "open_app",
            "volume",
            "mute",
            "unmute",
        ],
        "apps": list(APP_ALLOWLIST.keys()),
        "note": "One-shot only — no cron on agent",
    }
