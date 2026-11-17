import json
import re
from typing import Any

import structlog

from app.core.config import ai_settings
from app.core.errors import ProviderError
from app.rag.llm_client import OpenAICompatibleLLMClient
from app.rag.protocols import LLMClientProtocol

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT_SUMMARY = """Bạn là trợ lý thông minh chuyên phân tích và tóm tắt biên bản cuộc họp tiếng Việt chuyên nghiệp.
Nhiệm vụ của bạn là đọc toàn bộ nội dung bản ghi (transcript) và trích xuất thông tin có cấu trúc.

YÊU CẦU ĐẦU RA BẮT BUỘC:
Chỉ trả về DUY NHẤT một đối tượng JSON hợp lệ (không kèm markdown ```json bọc ngoài), tuân thủ định dạng sau:
{
  "executive_summary": "Đoạn văn tóm tắt ngắn gọn mục tiêu, nội dung thảo luận cốt lõi và kết quả đạt được của cuộc họp (3-5 câu).",
  "key_points": [
    "Ý chính thứ nhất đã thảo luận hoặc thống nhất",
    "Ý chính thứ hai..."
  ],
  "action_items": [
    {
      "description": "Nhiệm vụ hoặc đầu việc cụ thể cần thực hiện",
      "assignee": "Tên người chịu trách nhiệm hoặc 'Chưa phân công'",
      "status": "pending"
    }
  ]
}
"""

SYSTEM_PROMPT_RAG = """Bạn là trợ lý AI chuyên nghiệp phụ trách giải đáp thắc mắc về nội dung cuộc họp tiếng Việt dựa trên trích đoạn biên bản.
Bạn được cung cấp danh sách các đoạn trích từ cuộc họp trong thẻ <excerpts>.

QUY TẮC BẮT BUỘC:
1. Chỉ sử dụng thông tin có trong thẻ <excerpts> để trả lời.
2. Mỗi luận điểm hoặc thông tin quan trọng BẮT BUỘC phải kèm thẻ trích dẫn dạng [S01], [S02] tương ứng với đoạn trích chứng minh ngay sau câu nói.
3. Tuyệt đối không tự suy diễn, không bịa đặt mốc thời gian hay nội dung không có trong đoạn trích.
4. Nếu trong đoạn trích không có thông tin để trả lời câu hỏi, hãy trả lời chính xác: "Tôi không tìm thấy thông tin này trong nội dung cuộc họp."
"""


class MeetingSummaryGenerator:
    """Generates structured summaries and action items using LLMClientProtocol."""

    def __init__(
        self,
        provider: str | None = None,
        llm_client: LLMClientProtocol | None = None,
    ) -> None:
        """Initialize summary generator.

        Args:
            provider: LLM provider name (e.g. 'gemini' or 'openai').
            llm_client: Client implementing LLMClientProtocol. Defaults to OpenAICompatibleLLMClient.
        """
        self.provider = provider or ai_settings.llm_provider
        self.llm_client = llm_client or OpenAICompatibleLLMClient(provider=self.provider)

    async def generate_summary(self, full_transcript: str) -> dict[str, Any]:
        """Generate executive summary and action items from meeting transcript.

        Args:
            full_transcript: Full meeting text transcript.

        Returns:
            Dictionary containing executive_summary, key_points, and action_items.

        Raises:
            ProviderNotConfiguredError: If the LLM provider has no credentials.
            ProviderError: If the LLM fails or returns invalid JSON. No placeholder
                summary is ever produced.
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_SUMMARY},
            {
                "role": "user",
                "content": f"Dưới đây là toàn bộ transcript cuộc họp:\n\n{full_transcript}\n\nHãy phân tích và trả về JSON tóm tắt.",
            },
        ]

        content = await self.llm_client.generate_chat_completion(messages, temperature=0.2)
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        try:
            parsed = json.loads(content.strip())
        except json.JSONDecodeError as exc:
            logger.error("summary_json_invalid", provider=self.provider, error=str(exc))
            raise ProviderError("LLM returned an invalid summary payload.") from exc
        return {
            "executive_summary": parsed.get("executive_summary", ""),
            "key_points": parsed.get("key_points", []),
            "action_items": parsed.get("action_items", []),
        }


class RAGAnswerGenerator:
    """Generates answers with precise citations using LLMClientProtocol."""

    def __init__(
        self,
        provider: str | None = None,
        llm_client: LLMClientProtocol | None = None,
    ) -> None:
        """Initialize RAG answer generator.

        Args:
            provider: LLM provider name (e.g. 'gemini' or 'openai').
            llm_client: Client implementing LLMClientProtocol. Defaults to OpenAICompatibleLLMClient.
        """
        self.provider = provider or ai_settings.llm_provider
        self.llm_client = llm_client or OpenAICompatibleLLMClient(provider=self.provider)

    def format_excerpts(self, segments: list[dict[str, Any]]) -> str:
        """Format contextualized segments into XML excerpts with identifier tags.

        Args:
            segments: List of scored transcript segments.

        Returns:
            XML string formatted excerpts block.
        """
        lines = ["<excerpts>"]
        for idx, seg in enumerate(segments, 1):
            tag = f"[S{idx:02d}]"
            speaker = seg.get("speaker", "Người nói")
            start = float(seg.get("start", seg.get("start_time", 0.0)))
            end = float(seg.get("end", seg.get("end_time", 0.0)))
            start_m, start_s = int(start // 60), int(start % 60)
            end_m, end_s = int(end // 60), int(end % 60)
            content = seg.get("text", seg.get("content", "")).strip()
            lines.append(f"{tag} ({start_m:02d}:{start_s:02d}-{end_m:02d}:{end_s:02d}) {speaker}: {content}")
        lines.append("</excerpts>")
        return "\n".join(lines)

    async def answer_query(
        self,
        query: str,
        context_segments: list[dict[str, Any]],
        chat_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Generate answer with verified citations based on retrieved context segments.

        Args:
            query: User question about the meeting.
            context_segments: Top retrieved transcript chunks/segments.
            chat_history: Optional preceding conversational turns.

        Returns:
            Dictionary with 'answer' and 'citations' list.

        Raises:
            ProviderNotConfiguredError: If the LLM provider has no credentials.
            ProviderError: If the LLM request fails.
        """
        if not context_segments:
            return {
                "answer": "Tôi không tìm thấy thông tin này trong nội dung cuộc họp.",
                "citations": [],
            }

        excerpts_text = self.format_excerpts(context_segments)
        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT_RAG},
        ]

        if chat_history:
            for turn in chat_history[-4:]:
                messages.append({"role": turn.get("role", "user"), "content": turn.get("content", "")})

        user_content = (
            f"Dưới đây là các đoạn trích từ cuộc họp:\n\n{excerpts_text}\n\n"
            f"Câu hỏi: {query}\n\n"
            f"Hãy trả lời câu hỏi kèm mã trích dẫn [S...]."
        )
        messages.append({"role": "user", "content": user_content})

        raw_answer = (
            await self.llm_client.generate_chat_completion(messages, temperature=0.1)
        ).strip()

        citations: list[dict[str, Any]] = []
        seen_indices: set[int] = set()

        for match in re.finditer(r"\[S(\d+)\]", raw_answer):
            idx = int(match.group(1)) - 1
            if idx not in seen_indices and 0 <= idx < len(context_segments):
                seen_indices.add(idx)
                citations.append(self._build_citation(context_segments[idx], idx))

        if not citations and "không tìm thấy" not in raw_answer.lower():
            citations.append(self._build_citation(context_segments[0], 0))

        return {"answer": raw_answer, "citations": citations}

    @staticmethod
    def _build_citation(segment: dict[str, Any], index: int) -> dict[str, Any]:
        """Convert a retrieved segment into a citation payload."""
        return {
            "segment_id": str(segment.get("segment_id", segment.get("id", str(index)))),
            "speaker_label": segment.get("speaker", "Người nói"),
            "start_time": float(segment.get("start", segment.get("start_time", 0.0))),
            "end_time": float(segment.get("end", segment.get("end_time", 0.0))),
            "quote": (segment.get("text", segment.get("content", "")) or "")[:120],
        }
