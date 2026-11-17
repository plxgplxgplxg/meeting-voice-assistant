import json
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.ai_service_client import AgentStreamClient
from app.core.errors import AIUnavailableError, DomainError
from app.core.security import create_agent_token
from app.models.agent import AgentMessageModel
from app.models.meeting import MeetingModel
from app.models.user import UserModel
from app.schemas.agent import AgentActionResponse
from app.services.agent_actions import AgentActionService
from app.services.billing.quota_service import QuotaService
from app.services.chat_service import AI_ERROR_MESSAGE, ChatService

logger = structlog.get_logger(__name__)


def sse(event_type: str, data: dict[str, Any]) -> str:
    """Format one Server-Sent Event.

    Args:
        event_type: Event name (``token``, ``tool_start``, ``tool_end``, ``proposal``,
            ``citation``, ``done``, ``error``).
        data: JSON-serializable payload.

    Returns:
        The event as an SSE text frame.
    """
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@dataclass(frozen=True, slots=True)
class PreparedTurn:
    """A turn that passed every pre-check and is ready to stream.

    Attributes:
        message: The user's message.
        use_agent: True when the plan includes the assistant's tools, False for plain Q&A.
        user_id: Asking user, or None for share-link guests.
        conversation_id: Persisted conversation (agent path only).
        thread_id: LangGraph thread id for multi-turn state (agent path only).
        base_revision: Transcript revision the turn starts from.
    """

    message: str
    use_agent: bool
    user_id: uuid.UUID | None
    conversation_id: uuid.UUID | None
    thread_id: str | None
    base_revision: int


class AssistantService:
    """Runs one assistant turn: plain cited Q&A on the Free plan, the tool-using agent otherwise.

    Pre-checks run before streaming starts so failures are ordinary HTTP errors. The
    agent path commits the conversation and the user message before calling the AI
    service, because the agent calls back into this API (in other requests) and needs
    to see them.
    """

    def __init__(
        self,
        session: AsyncSession,
        chat: ChatService,
        agent_client: AgentStreamClient,
        actions: AgentActionService,
        quota: QuotaService,
    ) -> None:
        """Initialize the service.

        Args:
            session: Request session; also used while the response streams.
            chat: Plain Q&A and conversation storage.
            agent_client: Streams turns from the AI service.
            actions: Reads proposals created by the agent's tools.
            quota: Plan gating and the monthly question limit.
        """
        self.session = session
        self.chat = chat
        self.agent_client = agent_client
        self.actions = actions
        self.quota = quota

    async def prepare_turn(
        self, user: UserModel | None, meeting: MeetingModel, message: str
    ) -> PreparedTurn:
        """Check limits and persist the user's message when the agent will run.

        Args:
            user: Asking user, or None for share-link guests (plain Q&A only).
            meeting: Meeting already authorized for viewing.
            message: The user's message.

        Returns:
            A turn ready for :meth:`run_turn`.

        Raises:
            ConflictError: ``INDEX_NOT_READY`` for plain Q&A on an unindexed meeting.
            QuotaExceededError: ``RAG_QUESTION_LIMIT`` past the plan's monthly limit.
        """
        user_id = user.id if user else None
        use_agent = user is not None and await self.quota.agent_tools_enabled(user.id)
        if not use_agent:
            await self.chat.check_can_ask(meeting, user_id)
            return PreparedTurn(message, False, user_id, None, None, meeting.transcript_revision)

        assert user is not None
        await self.quota.assert_question_allowed(user.id)
        conversation = await self.chat.get_or_create_session(meeting.id, user.id)
        self.session.add(
            AgentMessageModel(
                conversation_id=conversation.id, role="user", content=message, citations=[]
            )
        )
        await self.session.commit()
        return PreparedTurn(
            message,
            True,
            user.id,
            conversation.id,
            conversation.langgraph_thread_id,
            meeting.transcript_revision,
        )

    async def run_turn(
        self, prepared: PreparedTurn, meeting: MeetingModel, user: UserModel | None
    ) -> AsyncIterator[str]:
        """Stream the turn's events as SSE frames.

        Args:
            prepared: Result of :meth:`prepare_turn`.
            meeting: The meeting being discussed.
            user: Asking user, or None for guests.

        Yields:
            SSE frames. Failures after streaming started arrive as an ``error`` event.
        """
        if prepared.use_agent and user is not None:
            async for frame in self._run_agent(prepared, meeting, user):
                yield frame
        else:
            async for frame in self._run_qa(prepared, meeting):
                yield frame

    async def _run_qa(self, prepared: PreparedTurn, meeting: MeetingModel) -> AsyncIterator[str]:
        try:
            answer = await self.chat.ask_question(meeting, prepared.user_id, prepared.message)
        except AIUnavailableError as exc:
            yield sse("error", {"code": exc.code, "message": exc.message})
            return
        except DomainError as exc:
            yield sse("error", {"code": exc.code, "message": exc.message})
            return
        yield sse("token", {"text": answer.content})
        for citation in answer.citations:
            yield sse("citation", citation)
        yield sse("done", {"message_id": str(answer.id)})

    async def _run_agent(
        self, prepared: PreparedTurn, meeting: MeetingModel, user: UserModel
    ) -> AsyncIterator[str]:
        assert prepared.conversation_id is not None
        delegated_token = create_agent_token(
            user.id, meeting.id, prepared.conversation_id, user.token_version
        )
        payload = {
            "thread_id": prepared.thread_id,
            "conversation_id": str(prepared.conversation_id),
            "meeting_id": str(meeting.id),
            "message": prepared.message,
            "delegated_token": delegated_token,
            "base_revision": prepared.base_revision,
        }

        text_parts: list[str] = []
        citations: list[dict[str, Any]] = []
        tool_calls: list[dict[str, Any]] = []
        failure: dict[str, str] | None = None
        try:
            async for event in self.agent_client.stream_turn(payload):
                event_type, data = event["type"], event["data"]
                if event_type == "token":
                    text_parts.append(str(data.get("text", "")))
                    yield sse("token", data)
                elif event_type == "tool_start":
                    tool_calls.append({"name": data.get("name"), "args": data.get("args", {})})
                    yield sse("tool_start", data)
                elif event_type == "tool_end":
                    yield sse("tool_end", data)
                elif event_type == "proposal":
                    frame = await self._proposal_frame(data, prepared.conversation_id)
                    if frame:
                        yield frame
                elif event_type == "citation":
                    citations.append(data)
                    yield sse("citation", data)
                elif event_type == "error":
                    failure = {
                        "code": str(data.get("code", "AGENT_ERROR")),
                        "message": str(data.get("message", "The assistant failed.")),
                    }
                    break
                elif event_type == "done":
                    break
        except AIUnavailableError as exc:
            failure = {"code": exc.code, "message": exc.message}

        message = AgentMessageModel(
            conversation_id=prepared.conversation_id,
            role="assistant",
            content=AI_ERROR_MESSAGE if failure else "".join(text_parts),
            citations=citations,
            tool_calls=tool_calls,
            status="error" if failure else "ok",
        )
        self.session.add(message)
        await self.session.flush()
        if failure:
            logger.warning("assistant_turn_failed", **failure)
            yield sse("error", failure)
        else:
            yield sse("done", {"message_id": str(message.id)})

    async def _proposal_frame(self, data: dict[str, Any], conversation_id: uuid.UUID) -> str | None:
        """Re-emit a proposal from the database so the client never sees unverified content."""
        try:
            action_id = uuid.UUID(str(data.get("action_id")))
        except ValueError:
            return None
        action = await self.actions.get_in_conversation(action_id, conversation_id)
        if action is None:
            return None
        return sse(
            "proposal", AgentActionResponse.model_validate(action).model_dump(mode="json")
        )
