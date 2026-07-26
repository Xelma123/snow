from fastapi import APIRouter

from app.api.v1 import chat, health, home, jobs, routines, sessions

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(chat.router)
api_router.include_router(home.router)
api_router.include_router(sessions.router)
api_router.include_router(jobs.router)
api_router.include_router(routines.router)
