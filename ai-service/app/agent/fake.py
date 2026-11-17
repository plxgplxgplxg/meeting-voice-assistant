from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class FakeAgentChatModel(BaseChatModel):
    """Chat model answering with a fixed demo message and never calling tools.

    Only used with ``ENVIRONMENT=development`` and ``AUDIO_PIPELINE_ENGINE=mock``.
    """

    @property
    def _llm_type(self) -> str:
        return "fake-agent"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "FakeAgentChatModel":
        """Accept tools and ignore them, so the graph can be built unchanged."""
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        text = "Dữ liệu mẫu: trợ lý đang chạy ở chế độ mock nên không gọi công cụ nào."
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])
