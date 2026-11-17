import json

import pytest

from app.core.errors import ProviderError, ProviderNotConfiguredError
from app.rag.generator import MeetingSummaryGenerator


class ScriptedLLM:
    def __init__(self, answer: str) -> None:
        self.answer = answer

    async def generate_chat_completion(self, messages, temperature: float = 0.2) -> str:
        return self.answer


@pytest.mark.asyncio
async def test_summary_without_api_key_raises_instead_of_returning_a_canned_summary() -> None:
    """With no LLM key the generator fails explicitly; no placeholder summary is produced."""
    generator = MeetingSummaryGenerator(provider="gemini")
    generator.llm_client.api_key = ""
    with pytest.raises(ProviderNotConfiguredError):
        await generator.generate_summary("Nội dung cuộc họp...")


@pytest.mark.asyncio
async def test_summary_parses_fenced_json() -> None:
    payload = json.dumps({"executive_summary": "Tóm tắt", "key_points": ["a"], "action_items": []})
    generator = MeetingSummaryGenerator(llm_client=ScriptedLLM(f"```json\n{payload}\n```"))
    result = await generator.generate_summary("text")
    assert result["executive_summary"] == "Tóm tắt"
    assert result["key_points"] == ["a"]


@pytest.mark.asyncio
async def test_summary_with_invalid_json_raises_provider_error() -> None:
    generator = MeetingSummaryGenerator(llm_client=ScriptedLLM("not json at all"))
    with pytest.raises(ProviderError):
        await generator.generate_summary("text")
