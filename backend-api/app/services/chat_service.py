import uuid
from typing import Any
import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.chat import ChatMessageModel, ChatSessionModel
from app.models.transcript import TranscriptSegmentModel

logger = structlog.get_logger(__name__)


class ChatService:
    """Service handling RAG conversational querying, chat session management, and message history."""

    def __init__(
        self,
        session: AsyncSession,
        ai_service_url: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize ChatService.

        Args:
            session: Active SQLAlchemy AsyncSession.
            ai_service_url: Microservice URL for AI queries. Defaults to settings.ai_service_url.
            http_client: Optional injected httpx.AsyncClient for HTTP calls.
        """
        self.session = session
        self.ai_service_url = (ai_service_url or settings.ai_service_url).rstrip("/")
        self.http_client = http_client

    async def get_or_create_session(self, meeting_id: uuid.UUID) -> ChatSessionModel:
        """Retrieve an active chat session or initialize a new one.

        Args:
            meeting_id: Target meeting UUID.

        Returns:
            Existing or newly persisted ChatSessionModel instance.
        """
        stmt = select(ChatSessionModel).where(ChatSessionModel.meeting_id == meeting_id)
        chat_session = await self.session.scalar(stmt)
        if not chat_session:
            chat_session = ChatSessionModel(meeting_id=meeting_id)
            self.session.add(chat_session)
            await self.session.flush()
        return chat_session

    async def list_messages(self, meeting_id: uuid.UUID) -> list[ChatMessageModel]:
        """Retrieve chat history for a meeting ordered chronologically.

        Args:
            meeting_id: Target meeting UUID.

        Returns:
            List of ChatMessageModel instances.
        """
        stmt = select(ChatSessionModel).where(ChatSessionModel.meeting_id == meeting_id)
        chat_session = await self.session.scalar(stmt)
        if not chat_session:
            return []

        result = await self.session.execute(
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == chat_session.id)
            .order_by(ChatMessageModel.created_at.asc())
        )
        return list(result.scalars().all())

    async def _fetch_meeting_segments(
        self, meeting_id: uuid.UUID
    ) -> list[TranscriptSegmentModel]:
        """Fetch all transcript segments belonging to a meeting in sequence.

        Args:
            meeting_id: Target meeting UUID.

        Returns:
            List of TranscriptSegmentModel instances ordered by sequence_order.
        """
        stmt = (
            select(TranscriptSegmentModel)
            .where(TranscriptSegmentModel.meeting_id == meeting_id)
            .order_by(TranscriptSegmentModel.sequence_order.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _fetch_recent_history(
        self, session_id: uuid.UUID, limit: int = 6
    ) -> list[dict[str, str]]:
        """Fetch recent conversational turns formatted for LLM context.

        Args:
            session_id: Chat session UUID.
            limit: Maximum count of recent messages to fetch.

        Returns:
            Chronologically ordered list of message dicts with role and content.
        """
        stmt = (
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session_id)
            .order_by(ChatMessageModel.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        messages = list(reversed(result.scalars().all()))
        return [{"role": m.role, "content": m.content} for m in messages]

    async def _query_ai_service_rag(
        self,
        meeting_id: uuid.UUID,
        query: str,
        segments: list[TranscriptSegmentModel],
        history: list[dict[str, str]],
    ) -> tuple[str, list[dict[str, Any]]]:
        """Send query to AI service RAG endpoint.

        Args:
            meeting_id: Target meeting UUID.
            query: Question asked by user.
            segments: Transcript segments to provide context.
            history: Recent conversation history.

        Returns:
            Tuple of (answer_text, citations_list).

        Raises:
            Exception: If HTTP request fails or response status is non-200.
        """
        segments_payload = [
            {
                "segment_id": str(s.id),
                "speaker": s.speaker_label,
                "start": s.start_time,
                "end": s.end_time,
                "text": s.content,
            }
            for s in segments
        ]

        payload = {
            "meeting_id": str(meeting_id),
            "query": query,
            "segments": segments_payload,
            "chat_history": history,
        }

        endpoint_url = f"{self.ai_service_url}/rag/query"

        if self.http_client is not None:
            resp = await self.http_client.post(endpoint_url, json=payload)
        else:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(endpoint_url, json=payload)

        if resp.status_code == 200:
            data = resp.json()
            answer = data.get("answer", "")
            citations = data.get("citations", [])
            return str(answer), list(citations)

        raise RuntimeError(
            f"AI Service query failed with status {resp.status_code}: {resp.text}"
        )

    def _fallback_search(
        self,
        query: str,
        segments: list[TranscriptSegmentModel],
    ) -> tuple[str, list[dict[str, Any]]]:
        """Compute keyword-based fallback response when AI microservice is unreachable.

        Args:
            query: Question asked by user.
            segments: List of transcript segments.

        Returns:
            Tuple of (answer_text, citations_list).
        """
        keywords = [w.lower() for w in query.split() if len(w) > 2]
        matched_segments = [
            s
            for s in segments
            if any(k in s.content.lower() for k in keywords)
        ]

        if matched_segments:
            first_match = matched_segments[0]
            answer = (
                f"Dựa trên nội dung cuộc họp, {first_match.speaker_label} đã trao đổi: "
                f"'{first_match.content}'."
            )
            citations = [
                {
                    "segment_id": str(s.id),
                    "speaker_label": s.speaker_label,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "quote": s.content[:120],
                }
                for s in matched_segments[:3]
            ]
            return answer, citations

        if segments:
            first = segments[0]
            answer = (
                f"Trong cuộc họp, các thành viên đã thảo luận về nội dung bắt đầu từ "
                f"[{int(first.start_time)}s]. Nội dung chính: '{first.content}'."
            )
            citations = [
                {
                    "segment_id": str(first.id),
                    "speaker_label": first.speaker_label,
                    "start_time": first.start_time,
                    "end_time": first.end_time,
                    "quote": first.content[:120],
                }
            ]
            return answer, citations

        return "Chưa có đủ dữ liệu phiên âm để trả lời câu hỏi này.", []

    async def ask_question(
        self,
        meeting_id: uuid.UUID,
        query: str,
    ) -> ChatMessageModel:
        """Process a user question, invoke RAG with fallback, and persist exchange.

        Args:
            meeting_id: Target meeting UUID.
            query: Question asked by user.

        Returns:
            Persisted assistant ChatMessageModel response.
        """
        chat_session = await self.get_or_create_session(meeting_id)

        user_msg = ChatMessageModel(
            session_id=chat_session.id,
            role="user",
            content=query,
            citations=[],
        )
        self.session.add(user_msg)
        await self.session.flush()

        segments = await self._fetch_meeting_segments(meeting_id)
        history = await self._fetch_recent_history(chat_session.id, limit=6)

        answer_text: str = ""
        citations: list[dict[str, Any]] = []

        try:
            answer_text, citations = await self._query_ai_service_rag(
                meeting_id=meeting_id,
                query=query,
                segments=segments,
                history=history,
            )
        except Exception as exc:
            logger.warning(
                "ai_service_rag_call_failed",
                meeting_id=str(meeting_id),
                error=str(exc),
            )
            answer_text, citations = self._fallback_search(query, segments)

        assistant_msg = ChatMessageModel(
            session_id=chat_session.id,
            role="assistant",
            content=answer_text,
            citations=citations,
        )
        self.session.add(assistant_msg)
        await self.session.commit()

        return assistant_msg
