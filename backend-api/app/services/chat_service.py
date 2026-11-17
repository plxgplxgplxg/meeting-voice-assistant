import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.ai_service_client import AIServiceClient
from app.core.errors import AIUnavailableError, ConflictError
from app.domain.enums import IndexStatus
from app.models.agent import AgentConversationModel, AgentMessageModel
from app.models.meeting import MeetingModel
from app.services.billing.quota_service import QuotaService
from app.services.retrieval_service import RetrievedChunk, TranscriptRetriever

logger = structlog.get_logger(__name__)

AI_ERROR_MESSAGE = "Trợ lý AI tạm thời không khả dụng. Vui lòng thử lại sau."
HISTORY_LIMIT = 6
RETRIEVAL_TOP_K = 5
ANSWERABLE_INDEX_STATES = frozenset({IndexStatus.READY, IndexStatus.STALE})


class ChatService:
    """Service handling meeting Q&A orchestration and per-user chat history.

    Retrieval happens in the backend, so the AI service receives at most
    ``RETRIEVAL_TOP_K`` chunks per question instead of the whole transcript.
    Callers must authorize VIEW access to the meeting first.
    """

    def __init__(
        self,
        session: AsyncSession,
        ai_client: AIServiceClient,
        retriever: TranscriptRetriever,
        quota: QuotaService | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            session: Active SQLAlchemy session.
            ai_client: Client for the AI service.
            retriever: Hybrid transcript retrieval.
            quota: Enforces the monthly question limit; defaults to one on ``session``.
        """
        self.session = session
        self.ai_client = ai_client
        self.retriever = retriever
        self.quota = quota or QuotaService(session)

    async def get_or_create_session(
        self, meeting_id: uuid.UUID, user_id: uuid.UUID | None
    ) -> AgentConversationModel:
        """Return the chat session for a (meeting, user) pair, creating it if needed.

        Args:
            meeting_id: Target meeting.
            user_id: Asking user, or None for share-link guests.

        Returns:
            Existing or newly created chat session.
        """
        chat_session = await self._find_session(meeting_id, user_id)
        if chat_session is None:
            chat_session = AgentConversationModel(meeting_id=meeting_id, user_id=user_id)
            self.session.add(chat_session)
            await self.session.flush()
        return chat_session

    async def list_messages(
        self, meeting_id: uuid.UUID, user_id: uuid.UUID | None
    ) -> list[AgentMessageModel]:
        """Return a user's chat history for a meeting in chronological order."""
        chat_session = await self._find_session(meeting_id, user_id)
        if chat_session is None:
            return []
        result = await self.session.execute(
            select(AgentMessageModel)
            .where(AgentMessageModel.conversation_id == chat_session.id)
            .order_by(AgentMessageModel.created_at.asc())
        )
        return list(result.scalars().all())

    async def check_can_ask(self, meeting: MeetingModel, user_id: uuid.UUID | None) -> None:
        """Verify a question can be answered now, before anything is persisted.

        Args:
            meeting: Meeting being asked about.
            user_id: Asking user, or None for share-link guests.

        Raises:
            ConflictError: With code ``INDEX_NOT_READY`` if the transcript is not indexed yet.
            QuotaExceededError: With code ``RAG_QUESTION_LIMIT`` past the monthly limit.
        """
        if meeting.index_status not in ANSWERABLE_INDEX_STATES:
            raise ConflictError(
                "The meeting is not indexed yet. Please try again once processing finishes.",
                code="INDEX_NOT_READY",
            )
        if user_id is not None:
            await self.quota.assert_question_allowed(user_id)

    async def ask_question(
        self, meeting: MeetingModel, user_id: uuid.UUID | None, query: str
    ) -> AgentMessageModel:
        """Answer a question about a meeting and persist the exchange.

        The user message is always persisted once the index is usable. When the AI
        service fails an assistant message with ``status="error"`` is stored and
        the failure is surfaced to the caller so the UI can offer a retry.

        Args:
            meeting: Meeting already authorized for viewing.
            user_id: Asking user, or None for share-link guests.
            query: Question text.

        Returns:
            The persisted assistant message.

        Raises:
            ConflictError: With code ``INDEX_NOT_READY`` if the transcript is not indexed yet.
            QuotaExceededError: With code ``RAG_QUESTION_LIMIT`` past the plan's monthly limit.
            AIUnavailableError: If the AI service could not produce an answer.
        """
        await self.check_can_ask(meeting, user_id)

        chat_session = await self.get_or_create_session(meeting.id, user_id)
        self.session.add(
            AgentMessageModel(conversation_id=chat_session.id, role="user", content=query, citations=[])
        )
        await self.session.flush()
        history = await self._fetch_recent_history(chat_session.id)

        try:
            chunks = await self.retriever.search(meeting.id, query, RETRIEVAL_TOP_K)
            answer, citations = await self.ai_client.rag_answer(
                query, [self._chunk_payload(c) for c in chunks], history
            )
        except AIUnavailableError as exc:
            self.session.add(
                AgentMessageModel(
                    conversation_id=chat_session.id,
                    role="assistant",
                    content=AI_ERROR_MESSAGE,
                    citations=[],
                    status="error",
                )
            )
            await self.session.flush()
            raise AIUnavailableError(exc.message, code=exc.code, commit_changes=True) from exc

        assistant_msg = AgentMessageModel(
            conversation_id=chat_session.id, role="assistant", content=answer, citations=citations
        )
        self.session.add(assistant_msg)
        await self.session.flush()
        return assistant_msg

    async def _find_session(
        self, meeting_id: uuid.UUID, user_id: uuid.UUID | None
    ) -> AgentConversationModel | None:
        owner_clause = (
            AgentConversationModel.user_id.is_(None)
            if user_id is None
            else AgentConversationModel.user_id == user_id
        )
        return await self.session.scalar(
            select(AgentConversationModel).where(
                AgentConversationModel.meeting_id == meeting_id, owner_clause
            )
        )

    async def _fetch_recent_history(self, conversation_id: uuid.UUID) -> list[dict[str, str]]:
        result = await self.session.execute(
            select(AgentMessageModel)
            .where(AgentMessageModel.conversation_id == conversation_id, AgentMessageModel.status == "ok")
            .order_by(AgentMessageModel.created_at.desc())
            .limit(HISTORY_LIMIT)
        )
        messages = list(reversed(result.scalars().all()))
        return [{"role": m.role, "content": m.content} for m in messages]

    @staticmethod
    def _chunk_payload(chunk: RetrievedChunk) -> dict[str, Any]:
        return {
            "segment_id": str(chunk.segment_ids[0]) if chunk.segment_ids else str(chunk.id),
            "speaker": chunk.speaker_label,
            "start": chunk.start_time,
            "end": chunk.end_time,
            "text": chunk.text,
        }
