import json


class FakeLLMClient:
    """LLM client with canned outputs for development with ``AUDIO_PIPELINE_ENGINE=mock``."""

    async def generate_chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
    ) -> str:
        """Return a canned summary JSON or a canned cited answer.

        Args:
            messages: Chat messages; the system prompt selects the response shape.
            temperature: Ignored.

        Returns:
            Deterministic demo content.
        """
        system_prompt = messages[0]["content"] if messages else ""
        if "executive_summary" in system_prompt:
            return json.dumps(
                {
                    "executive_summary": "Dữ liệu mẫu: cuộc họp rà soát tiến độ dự án.",
                    "key_points": ["Dữ liệu mẫu: chuyển sang kiến trúc API-first."],
                    "action_items": [
                        {
                            "description": "Dữ liệu mẫu: hoàn thiện tài liệu.",
                            "assignee": "Chưa phân công",
                            "status": "pending",
                        }
                    ],
                },
                ensure_ascii=False,
            )
        return "Dữ liệu mẫu: nội dung được đề cập trong cuộc họp [S01]."
