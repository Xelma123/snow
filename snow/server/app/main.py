"""Snow API — server-centric home brain."""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import api_router
from app.config import OPENROUTER_MODEL, get_settings, validate_settings
from app.core.scheduler import start_scheduler, stop_scheduler
from app.http_client import shutdown_http, startup_http
from app.integrations.ha import HomeAssistant, HomeAssistantError
from app.storage.db import init_db

logger = logging.getLogger("snow")
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s rid=%(request_id)s %(message)s",
)
# default filter if no request_id
old_factory = logging.getLogRecordFactory()


def _record_factory(*args, **kwargs):  # type: ignore[no-untyped-def]
    record = old_factory(*args, **kwargs)
    if not hasattr(record, "request_id"):
        record.request_id = "-"
    return record


logging.setLogRecordFactory(_record_factory)

WEB_DIR = Path(__file__).resolve().parents[2] / "web"


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    await init_db(settings)
    await startup_http()
    for w in validate_settings(settings):
        logger.warning(w)
    logger.info(
        "Snow ready model=%s data=%s light=%s tv=%s",
        OPENROUTER_MODEL,
        settings.data_dir,
        settings.ha_default_light,
        settings.ha_default_tv,
    )
    try:
        players = await HomeAssistant(settings).list_by_domain("media_player")
        if players:
            logger.info(
                "HA media_players: %s",
                ", ".join(f"{p['entity_id']}({p['state']})" for p in players[:8]),
            )
        else:
            logger.warning("HA'da media_player yok — TV komutları çalışmayabilir")
    except HomeAssistantError as e:
        logger.warning("HA discovery atlandı: %s", e)
    except Exception as e:  # noqa: BLE001
        logger.warning("HA discovery hatası: %s", e)

    start_scheduler()
    yield
    await stop_scheduler()
    await shutdown_http()


app = FastAPI(
    title="Snow",
    version="1.2.0",
    description="Self-hosted home assistant brain",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())[:12]
    request.state.request_id = rid
    t0 = time.time()
    response = await call_next(request)
    response.headers["X-Request-Id"] = rid
    response.headers["X-Process-Time-Ms"] = str(int((time.time() - t0) * 1000))
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exc_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exc_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exc_handler(request: Request, exc: Exception):
    logger.exception("unhandled %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Sunucu hatası",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


app.include_router(api_router)

# Compat aliases (clients may use /api/chat without v1)
from app.api.v1 import chat as chat_mod  # noqa: E402
from app.api.v1 import health as health_mod  # noqa: E402

app.include_router(health_mod.router, prefix="/api")
app.include_router(chat_mod.router, prefix="/api")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/voice")
async def voice_ui() -> FileResponse:
    """Phone-first push-to-talk voice bridge (STT/TTS on device)."""
    return FileResponse(WEB_DIR / "voice.html")


@app.get("/manifest.json")
async def manifest() -> FileResponse:
    return FileResponse(WEB_DIR / "manifest.json")


@app.get("/manifest-voice.json")
async def manifest_voice() -> FileResponse:
    return FileResponse(WEB_DIR / "manifest-voice.json")


if WEB_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
