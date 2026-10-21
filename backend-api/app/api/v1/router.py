from fastapi import APIRouter

from app.api.v1.endpoints import chat, exports, meetings, summaries, transcripts

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(meetings.router)
api_router.include_router(transcripts.router)
api_router.include_router(summaries.router)
api_router.include_router(chat.router)
api_router.include_router(exports.router)
