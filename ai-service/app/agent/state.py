from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class AgentState(TypedDict):
    """Graph state of one assistant conversation.

    The checkpointer persists it per ``thread_id`` so follow-up questions keep their context.

    Attributes:
        messages: Conversation so far, merged with LangGraph's ``add_messages`` reducer.
        meeting_id: Meeting the conversation is about.
        conversation_id: Backend conversation id, for tracing.
        revision: Transcript revision the current turn started from.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    meeting_id: str
    conversation_id: str
    revision: int


class TurnContext:
    """Per-turn dependencies and outputs, passed to tools through ``config["configurable"]``.

    Holds the backend client bound to the delegated token (the token itself is never
    given to the model) and collects what the stream adapter needs: citation sources
    and proposals created during the turn.
    """

    def __init__(
        self,
        backend: Any,
        meeting_id: str,
        conversation_id: str,
        base_revision: int,
    ) -> None:
        """Initialize the context.

        Args:
            backend: ``BackendToolClient`` executing calls as the delegated user.
            meeting_id: The meeting the turn is scoped to.
            conversation_id: Backend conversation id.
            base_revision: Transcript revision the turn started from; proposals are based on it.
        """
        self.backend = backend
        self.meeting_id = meeting_id
        self.conversation_id = conversation_id
        self.base_revision = base_revision
        self.sources: dict[str, dict[str, Any]] = {}
        self.proposals: list[dict[str, Any]] = []
        self.tool_calls = 0
