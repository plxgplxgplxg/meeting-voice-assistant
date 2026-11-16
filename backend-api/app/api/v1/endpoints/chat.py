import uuid
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.schemas.chat import ChatMessageResponse, ChatQueryRequest
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/{meeting_id}/messages", response_model=list[ChatMessageResponse])
async def list_chat_messages(
    meeting_id: uuid.UUID, db: DatabaseSession
) -> list[ChatMessageResponse]:
    """Retrieve chat history for a meeting in chronological order.

    Args:
        meeting_id: Target meeting UUID.
        db: Active SQLAlchemy AsyncSession.

    Returns:
        List of ChatMessageResponse objects.
    """
    service = ChatService(db)
    messages = await service.list_messages(meeting_id)
    return [ChatMessageResponse.model_validate(m) for m in messages]


@router.post("/{meeting_id}", response_model=ChatMessageResponse)
async def ask_question(
    meeting_id: uuid.UUID, payload: ChatQueryRequest, db: DatabaseSession
) -> ChatMessageResponse:
    """Ask questions regarding a specific meeting session with citation retrieval.

    Args:
        meeting_id: Target meeting UUID.
        payload: Chat query payload containing user's question.
        db: Active SQLAlchemy AsyncSession.

    Returns:
        ChatMessageResponse containing assistant answer and citations.
    """
    service = ChatService(db)
    assistant_msg = await service.ask_question(meeting_id, payload.query)
    return ChatMessageResponse.model_validate(assistant_msg)
