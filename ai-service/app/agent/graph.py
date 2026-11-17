from collections.abc import Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, ToolException
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import RetryPolicy
from pydantic import ValidationError

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.state import AgentState
from app.agent.tools import CONNECTION_ERRORS

RECOVERABLE_TOOL_ERRORS = (ValidationError, ToolException)
TOOL_RETRY = RetryPolicy(max_attempts=2, initial_interval=0.2, retry_on=CONNECTION_ERRORS)


def build_graph(
    llm: BaseChatModel,
    tools: Sequence[BaseTool],
    checkpointer: BaseCheckpointSaver | None,
) -> CompiledStateGraph:
    """Compile the assistant graph: ``agent -> tools -> agent`` until the model stops calling tools.

    Malformed tool arguments come back to the model as an error message so it can
    correct them. Connection errors that never reached the backend are retried once.
    Any other tool exception propagates and ends the turn with an error event, so a
    write is never retried when it might already have happened.

    Args:
        llm: Chat model supporting tool calling.
        tools: Tools the model may call.
        checkpointer: Persists conversation state per thread id; None disables persistence.

    Returns:
        The compiled graph.
    """
    model = llm.bind_tools(list(tools))

    async def agent(state: AgentState, config: RunnableConfig) -> dict[str, list]:
        reply = await model.ainvoke([SystemMessage(SYSTEM_PROMPT), *state["messages"]], config)
        return {"messages": [reply]}

    builder = StateGraph(AgentState)
    builder.add_node("agent", agent)
    builder.add_node(
        "tools",
        ToolNode(list(tools), handle_tool_errors=RECOVERABLE_TOOL_ERRORS),
        retry_policy=TOOL_RETRY,
    )
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    builder.add_edge("tools", "agent")
    return builder.compile(checkpointer=checkpointer)
