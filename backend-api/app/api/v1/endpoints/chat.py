import uuid
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.schemas.chat import ChatMessageResponse, ChatQueryRequest

router = APIRouter(prefix="/chat", tags=["Chat"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("/{meeting_id}", response_model=ChatMessageResponse)
async def ask_question(
    meeting_id: uuid.UUID, payload: ChatQueryRequest, db: DatabaseSession
) -> ChatMessageResponse:
    """Ask questions regarding a specific meeting session with citation retrieval."""
    return ChatMessageResponse(
        id=uuid.uuid4(),
        role="assistant",
        content="Meeting QA is initialized.",
        citations=[],
        created_at=uuid.uuid1().time,
    )
