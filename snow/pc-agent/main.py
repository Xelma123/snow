"""Snow PC Agent — thin Windows hand for Acer brain.

Run on MSI (awake session):
  set SNOW_PC_AGENT_TOKEN=same-as-acer
  python -m uvicorn main:app --host 0.0.0.0 --port 8790

Only LAN + Bearer token. No free shell.
"""

from __future__ import annotations

import logging
import os
import socket
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from tools import desktop_action, load_macros, manifest, power_action, run_macro

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("snow.pc_agent")

APP_DIR = Path(__file__).resolve().parent
MACROS_PATH = APP_DIR / "macros.yaml"
TOKEN = (os.environ.get("SNOW_PC_AGENT_TOKEN") or "").strip()
PORT = int(os.environ.get("SNOW_PC_AGENT_PORT") or "8790")

app = FastAPI(title="Snow PC Agent", version="1.0.0")


def require_auth(authorization: str | None = Header(default=None)) -> None:
    if not TOKEN:
        raise HTTPException(
            status_code=503,
            detail="SNOW_PC_AGENT_TOKEN tanımlı değil",
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token gerekli")
    got = authorization[7:].strip()
    if got != TOKEN:
        raise HTTPException(status_code=401, detail="Token reddedildi")


class PowerBody(BaseModel):
    action: str = Field(..., description="sleep|shutdown|reboot|lock")


class DesktopBody(BaseModel):
    action: str
    value: str | int | float | None = None


class MacroBody(BaseModel):
    id: str


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "service": "snow-pc-agent",
        "hostname": socket.gethostname(),
        "user": os.environ.get("USERNAME") or os.environ.get("USER") or "",
    }


@app.get("/v1/manifest", dependencies=[Depends(require_auth)])
def v1_manifest() -> dict:
    m = manifest()
    m["macros"] = list(load_macros(MACROS_PATH).keys())
    return m


@app.post("/v1/power", dependencies=[Depends(require_auth)])
def v1_power(body: PowerBody) -> dict:
    result = power_action(body.action)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "failed")
    logger.info("power %s", body.action)
    return result


@app.post("/v1/desktop", dependencies=[Depends(require_auth)])
def v1_desktop(body: DesktopBody) -> dict:
    result = desktop_action(body.action, body.value)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "failed")
    logger.info("desktop %s value=%s", body.action, body.value)
    return result


@app.post("/v1/macro", dependencies=[Depends(require_auth)])
def v1_macro(body: MacroBody) -> dict:
    result = run_macro(body.id, MACROS_PATH)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "failed")
    logger.info("macro %s", body.id)
    return result


if __name__ == "__main__":
    import uvicorn

    if not TOKEN:
        print("WARNING: set SNOW_PC_AGENT_TOKEN before production use")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
