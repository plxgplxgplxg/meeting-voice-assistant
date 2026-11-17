from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.agent.fake import FakeAgentChatModel
from app.core.config import ai_settings
from app.core.errors import ProviderNotConfiguredError

LLM_TIMEOUT_SECONDS = 60


def build_chat_model() -> BaseChatModel:
    """Create the tool-calling chat model for the configured provider.

    Gemini is reached through its OpenAI-compatible endpoint, so one client class
    covers both providers.

    Returns:
        The chat model, or a canned fake in development with the mock engine.

    Raises:
        ProviderNotConfiguredError: If the selected provider has no API key.
    """
    if ai_settings.use_mock_engine and not ai_settings.is_production:
        return FakeAgentChatModel()
    if not ai_settings.llm_api_key:
        raise ProviderNotConfiguredError(f"LLM provider not configured: {ai_settings.llm_provider}")
    return ChatOpenAI(
        model=ai_settings.llm_model_name,
        api_key=SecretStr(ai_settings.llm_api_key),
        base_url=ai_settings.llm_base_url,
        temperature=0.1,
        streaming=True,
        timeout=LLM_TIMEOUT_SECONDS,
        max_retries=1,
    )
