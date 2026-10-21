import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessageModel, ChatSessionModel


class ChatService:
    """Service handling RAG conversational querying and history."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create_session(self, meeting_id: uuid.UUID) -> ChatSessionModel:
        """Retrieve an active chat session or initialize a new one."""
        session = ChatSessionModel(meeting_id=meeting_id)
        self.session.add(session)
        await self.session.flush()
        return session
