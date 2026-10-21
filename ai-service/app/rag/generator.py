from typing import Any


class MeetingSummaryGenerator:
    """Generates structured summaries and action items using LLM."""

    async def generate_summary(self, full_transcript: str) -> dict[str, Any]:
        """Generate executive summary and action items from full meeting transcript.

        Args:
            full_transcript: Full meeting text transcript.

        Returns:
            Dictionary containing executive_summary and action_items.
        """
        return {
            "executive_summary": "Tóm tắt cuộc họp khởi tạo.",
            "key_points": ["Thảo luận tiến độ", "Phân công nhiệm vụ"],
            "action_items": [
                {
                    "description": "Cài đặt pipeline ASR",
                    "assignee": "Nguyen Phuong Linh",
                    "status": "pending",
                }
            ],
        }
