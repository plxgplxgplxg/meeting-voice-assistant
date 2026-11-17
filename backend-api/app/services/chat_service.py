import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.ai_service_client import AIServiceClient
from app.core.errors import AIUnavailableError
from app.models.chat import ChatMessageModel, ChatSessionModel
from app.models.transcript import TranscriptSegmentModel

logger = structlog.get_logger(__name__)

AI_ERROR_MESSAGE = "Trợ lý AI tạm thời không khả dụng. Vui lòng thử lại sau."
HISTORY_LIMIT = 6


class ChatService:
    """Service handling meeting Q&A orchestration and per-user chat history.

    Callers must authorize VIEW access to the meeting first.
    """

    def __init__(self, session: AsyncSession, ai_client: AIServiceClient) -> None:
        """Initialize the service.

        Args:
            session: Active SQLAlchemy session.
            ai_client: Client for the AI service.
        """
        self.session = session
        self.ai_client = ai_client

    async def get_or_create_session(
        self, meeting_id: uuid.UUID, user_id: uuid.UUID | None
    ) -> ChatSessionModel:
        """Return the chat session for a (meeting, user) pair, creating it if needed.

        Args:
            meeting_id: Target meeting.
            user_id: Asking user, or None for share-link guests.

        Returns:
            Existing or newly created chat session.
        """
        chat_session = await self._find_session(meeting_id, user_id)
        if chat_session is None:
            chat_session = ChatSessionModel(meeting_id=meeting_id, user_id=user_id)
            self.session.add(chat_session)
            await self.session.flush()
        return chat_session

    async def list_messages(
        self, meeting_id: uuid.UUID, user_id: uuid.UUID | None
    ) -> list[ChatMessageModel]:
        """Return a user's chat history for a meeting in chronological order."""
        chat_session = await self._find_session(meeting_id, user_id)
        if chat_session is None:
            return []
        result = await self.session.execute(
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == chat_session.id)
            .order_by(ChatMessageModel.created_at.asc())
        )
        return list(result.scalars().all())

    async def ask_question(
        self, meeting_id: uuid.UUID, user_id: uuid.UUID | None, query: str
    ) -> ChatMessageModel:
        """Answer a question about a meeting and persist the exchange.

        The user message is always persisted. When the AI service fails an
        assistant message with ``status="error"`` is stored and the failure is
        surfaced to the caller, so the UI can offer a retry. No keyword-match
        answer is ever presented as an assistant answer.

        Args:
            meeting_id: Target meeting.
            user_id: Asking user, or None for share-link guests.
            query: Question text.

        Returns:
            The persisted assistant message.

        Raises:
            AIUnavailableError: If the AI service could not produce an answer.
        """
        chat_session = await self.get_or_create_session(meeting_id, user_id)
        self.session.add(
            ChatMessageModel(session_id=chat_session.id, role="user", content=query, citations=[])
        )
        await self.session.flush()

        segments = await self._fetch_meeting_segments(meeting_id)
        history = await self._fetch_recent_history(chat_session.id)

        try:
            answer, citations = await self.ai_client.rag_query(
                meeting_id=str(meeting_id),
                query=query,
                segments=[self._segment_payload(s) for s in segments],
                chat_history=history,
            )
        except AIUnavailableError as exc:
            self.session.add(
                ChatMessageModel(
                    session_id=chat_session.id,
                    role="assistant",
                    content=AI_ERROR_MESSAGE,
                    citations=[],
                    status="error",
                )
            )
            await self.session.flush()
            raise AIUnavailableError(
                exc.message, code=exc.code, commit_changes=True
            ) from exc

        assistant_msg = ChatMessageModel(
            session_id=chat_session.id, role="assistant", content=answer, citations=citations
        )
        self.session.add(assistant_msg)
        await self.session.flush()
        return assistant_msg

    async def _find_session(
        self, meeting_id: uuid.UUID, user_id: uuid.UUID | None
    ) -> ChatSessionModel | None:
        owner_clause = (
            ChatSessionModel.user_id.is_(None)
            if user_id is None
            else ChatSessionModel.user_id == user_id
        )
        return await self.session.scalar(
            select(ChatSessionModel).where(ChatSessionModel.meeting_id == meeting_id, owner_clause)
        )

    async def _fetch_meeting_segments(self, meeting_id: uuid.UUID) -> list[TranscriptSegmentModel]:
        result = await self.session.execute(
            select(TranscriptSegmentModel)
            .where(TranscriptSegmentModel.meeting_id == meeting_id)
            .order_by(TranscriptSegmentModel.sequence_order.asc())
        )
        return list(result.scalars().all())

    async def _fetch_recent_history(self, session_id: uuid.UUID) -> list[dict[str, str]]:
        result = await self.session.execute(
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session_id, ChatMessageModel.status == "ok")
            .order_by(ChatMessageModel.created_at.desc())
            .limit(HISTORY_LIMIT)
        )
        messages = list(reversed(result.scalars().all()))
        return [{"role": m.role, "content": m.content} for m in messages]

    @staticmethod
    def _segment_payload(segment: TranscriptSegmentModel) -> dict[str, Any]:
        return {
            "segment_id": str(segment.id),
            "speaker": segment.speaker_label,
            "start": segment.start_time,
            "end": segment.end_time,
            "text": segment.content,
        }
