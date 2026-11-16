from fastapi import APIRouter

from app.api.v1.endpoints import (
    audio,
    auth,
    chat,
    exports,
    live_ws,
    meetings,
    payments,
    plans,
    projects,
    summaries,
    transcripts,
    users,
)

api_router = APIRouter(prefix="/api/v1")

# Core & Auxiliary Routers
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(projects.router)
api_router.include_router(meetings.router)
api_router.include_router(audio.router)
api_router.include_router(transcripts.router)
api_router.include_router(summaries.router)
api_router.include_router(chat.router)
api_router.include_router(exports.router)
api_router.include_router(plans.router)
api_router.include_router(payments.router)
api_router.include_router(live_ws.router)
