import pytest
from app.rag.generator import MeetingSummaryGenerator


@pytest.mark.asyncio
async def test_summary_fallback_when_no_api_key() -> None:
    """Ensure graceful structured summary when LLM API keys are unconfigured."""
    generator = MeetingSummaryGenerator()
    result = await generator.generate_summary("Nội dung cuộc họp demo...")
    assert "executive_summary" in result
    assert "key_points" in result
    assert "action_items" in result
    assert isinstance(result["key_points"], list)
    assert isinstance(result["action_items"], list)
    assert len(result["key_points"]) > 0
