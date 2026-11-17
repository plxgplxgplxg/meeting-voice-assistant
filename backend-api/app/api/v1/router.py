from fastapi import APIRouter

from app.api.v1.endpoints import (
    assistant,
    audio,
    auth,
    chat,
    exports,
    meetings,
    payments,
    plans,
    processing,
    projects,
    summaries,
    transcripts,
    users,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(projects.router)
api_router.include_router(meetings.router)
api_router.include_router(audio.router)
api_router.include_router(transcripts.router)
api_router.include_router(summaries.router)
api_router.include_router(chat.router)
api_router.include_router(assistant.router)
api_router.include_router(exports.router)
api_router.include_router(processing.router)
api_router.include_router(plans.router)
api_router.include_router(payments.router)

# Deprecated aliases kept until the frontend moves to the nested /meetings/{id}/... routes
api_router.include_router(audio.legacy_router)
api_router.include_router(transcripts.legacy_router)
api_router.include_router(summaries.legacy_router)
api_router.include_router(chat.legacy_router)
api_router.include_router(exports.legacy_router)
