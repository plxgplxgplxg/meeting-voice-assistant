import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import structlog
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from langgraph.errors import GraphRecursionError
from langgraph.graph.state import CompiledStateGraph

from app.agent.backend_client import BackendToolClient
from app.agent.state import TurnContext
from app.core.errors import ServiceError

logger = structlog.get_logger(__name__)

CITATION_PATTERN = re.compile(r"\[(S\d+)\]")
SUMMARY_LIMIT = 200


@dataclass(frozen=True, slots=True)
class AgentTurnRequest:
    """One user message to run through the agent."""

    thread_id: str
    conversation_id: str
    meeting_id: str
    message: str
    base_revision: int


def chunk_text(chunk: AIMessageChunk) -> str:
    """Extract plain text from a streamed model chunk (string or list of content parts)."""
    content = chunk.content
    if isinstance(content, str):
        return content
    return "".join(
        part.get("text", "") for part in content if isinstance(part, dict) and part.get("type") == "text"
    )


class AgentTurnRunner:
    """Runs a turn on the compiled graph and translates LangGraph output into SSE-ready events.

    Events: ``token``, ``tool_start``, ``tool_end``, ``proposal``, ``citation``, ``done``, ``error``.
    The runner owns the per-turn context, so the delegated token only ever lives in the
    backend client and never enters model-visible state.
    """

    def __init__(self, graph: CompiledStateGraph, recursion_limit: int) -> None:
        """Initialize the runner.

        Args:
            graph: Compiled assistant graph.
            recursion_limit: Maximum graph steps per turn.
        """
        self.graph = graph
        self.recursion_limit = recursion_limit

    async def run(
        self, request: AgentTurnRequest, backend: BackendToolClient
    ) -> AsyncIterator[dict[str, Any]]:
        """Run one turn and yield events as they happen.

        Args:
            request: The user's message and conversation identifiers.
            backend: Backend client bound to the delegated token.

        Yields:
            Events ``{"type": ..., "data": {...}}``. Failures arrive as an ``error`` event.
        """
        context = TurnContext(backend, request.meeting_id, request.conversation_id, request.base_revision)
        config = {
            "configurable": {"thread_id": request.thread_id, "turn": context},
            "recursion_limit": self.recursion_limit,
        }
        graph_input = {
            "messages": [HumanMessage(request.message)],
            "meeting_id": request.meeting_id,
            "conversation_id": request.conversation_id,
            "revision": request.base_revision,
        }

        answer: list[str] = []
        announced: set[str] = set()
        emitted_proposals = 0
        try:
            async for mode, data in self.graph.astream(
                graph_input, config, stream_mode=["messages", "updates"]
            ):
                if mode == "messages":
                    chunk, metadata = data
                    if isinstance(chunk, AIMessageChunk) and metadata.get("langgraph_node") == "agent":
                        text = chunk_text(chunk)
                        if text:
                            answer.append(text)
                            yield {"type": "token", "data": {"text": text}}
                    continue

                for node, update in data.items():
                    for message in (update or {}).get("messages", []):
                        if node == "agent" and isinstance(message, AIMessage):
                            for call in message.tool_calls:
                                if call["id"] not in announced:
                                    announced.add(call["id"])
                                    context.tool_calls += 1
                                    yield {
                                        "type": "tool_start",
                                        "data": {"name": call["name"], "args": call["args"]},
                                    }
                        elif node == "tools" and isinstance(message, ToolMessage):
                            yield {
                                "type": "tool_end",
                                "data": {
                                    "name": message.name,
                                    "summary": str(message.content)[:SUMMARY_LIMIT],
                                },
                            }
                            while emitted_proposals < len(context.proposals):
                                yield {"type": "proposal", "data": context.proposals[emitted_proposals]}
                                emitted_proposals += 1
        except GraphRecursionError:
            yield {
                "type": "error",
                "data": {"code": "AGENT_RECURSION_LIMIT", "message": "The assistant took too many steps."},
            }
            return
        except ServiceError as exc:
            yield {"type": "error", "data": {"code": exc.code, "message": exc.message}}
            return
        except Exception as exc:
            logger.exception("agent_turn_failed", conversation_id=request.conversation_id)
            yield {"type": "error", "data": {"code": "AGENT_ERROR", "message": type(exc).__name__}}
            return

        for label in dict.fromkeys(CITATION_PATTERN.findall("".join(answer))):
            source = context.sources.get(label)
            if source:
                yield {"type": "citation", "data": source}
        yield {"type": "done", "data": {}}
