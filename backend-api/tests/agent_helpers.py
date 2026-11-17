import json
import uuid
from typing import Any

from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_agent_token
from app.models.meeting import MeetingModel
from app.models.transcript import TranscriptSegmentModel
from app.models.user import UserModel
from app.services.chat_service import ChatService
from tests.conftest import Account, FakeAIClient, FakeRetriever, MakeMeeting

SEGMENT_ROWS = [
    ("Speaker 1", 0.0, 10.0, "Xin chào, hôm nay họp về Gemany."),
    ("Speaker 1", 10.0, 20.0, "Gemany là nhà cung cấp mô hình."),
    ("Speaker 2", 20.0, 30.0, "Đồng ý, ta dùng Gemany cho bản demo."),
    ("Speaker 2", 30.0, 40.0, "Hẹn gặp lại."),
]


async def seed_meeting(db: AsyncSession, make_meeting: MakeMeeting, owner_id: uuid.UUID, **kwargs: Any):
    """Create a ready meeting with a four-segment transcript; returns the meeting and its segments."""
    meeting = await make_meeting(owner_id, **kwargs)
    segments = []
    for order, (speaker, start, end, text) in enumerate(SEGMENT_ROWS, start=1):
        segment = TranscriptSegmentModel(
            meeting_id=meeting.id, speaker_label=speaker, start_time=start, end_time=end,
            content=text, sequence_order=order,
        )
        db.add(segment)
        segments.append(segment)
    await db.flush()
    return meeting, segments


async def delegated_headers(
    db: AsyncSession, user: Account, meeting: MeetingModel, fake_ai: FakeAIClient | None = None
) -> dict[str, str]:
    """Headers the AI service would send for a tool call on behalf of ``user``."""
    row = await db.get(UserModel, user.id)
    conversation = await ChatService(
        db, fake_ai or FakeAIClient(), FakeRetriever()
    ).get_or_create_session(meeting.id, user.id)
    token = create_agent_token(user.id, meeting.id, conversation.id, row.token_version)
    return {"Authorization": f"Bearer {token}", "X-Service-Token": settings.ai_service_token}


def parse_sse(response: Response) -> list[tuple[str, dict[str, Any]]]:
    """Decode a Server-Sent Events body into (event, data) pairs."""
    events: list[tuple[str, dict[str, Any]]] = []
    for frame in response.text.strip().split("\n\n"):
        lines = frame.splitlines()
        if len(lines) >= 2 and lines[0].startswith("event:"):
            events.append((lines[0].removeprefix("event:").strip(), json.loads(lines[1].removeprefix("data:"))))
    return events


async def propose(
    client: AsyncClient, meeting_id: uuid.UUID, headers: dict[str, str], body: dict[str, Any]
) -> Response:
    """Call the internal proposal tool."""
    return await client.post(
        f"/internal/agent/v1/meetings/{meeting_id}/agent-actions", headers=headers, json=body
    )
