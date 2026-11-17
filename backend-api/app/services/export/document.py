import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meeting import MeetingModel
from app.models.summary import ActionItemModel, SummaryModel
from app.models.transcript import TranscriptSegmentModel


@dataclass(frozen=True, slots=True)
class SegmentView:
    """Transcript segment as exported."""

    id: uuid.UUID
    speaker: str
    start: float
    end: float
    text: str


@dataclass(frozen=True, slots=True)
class ActionItemView:
    """Action item as exported."""

    id: uuid.UUID
    description: str
    assignee: str
    status: str


@dataclass(frozen=True, slots=True)
class MeetingDocument:
    """Read model of a meeting assembled once and shared by every renderer.

    Attributes:
        meeting_id: Meeting identifier.
        title: Meeting title.
        status: Processing status.
        created_at: Creation time.
        duration_seconds: Recording length.
        revision: Transcript revision the document reflects.
        segments: Transcript in order.
        executive_summary: Summary text, if one exists.
        key_points: Summary bullet points.
        action_items: Action items in creation order.
    """

    meeting_id: uuid.UUID
    title: str
    status: str
    created_at: datetime
    duration_seconds: float
    revision: int
    segments: list[SegmentView]
    executive_summary: str | None = None
    key_points: list[Any] = field(default_factory=list)
    action_items: list[ActionItemView] = field(default_factory=list)


class MeetingDocumentLoader:
    """Loads the meeting, transcript, summary and action items in one place.

    Export, artifact generation and the agent all read through this loader instead
    of each issuing their own transcript queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def load(self, meeting: MeetingModel) -> MeetingDocument:
        """Assemble the read model for a meeting.

        Args:
            meeting: Meeting already authorized for viewing.

        Returns:
            The assembled document.
        """
        segments = (
            await self.session.scalars(
                select(TranscriptSegmentModel)
                .where(TranscriptSegmentModel.meeting_id == meeting.id)
                .order_by(TranscriptSegmentModel.sequence_order)
            )
        ).all()
        summary = await self.session.scalar(
            select(SummaryModel).where(SummaryModel.meeting_id == meeting.id)
        )
        items = (
            await self.session.scalars(
                select(ActionItemModel)
                .where(ActionItemModel.meeting_id == meeting.id)
                .order_by(ActionItemModel.created_at)
            )
        ).all()
        return MeetingDocument(
            meeting_id=meeting.id,
            title=meeting.title,
            status=meeting.status,
            created_at=meeting.created_at,
            duration_seconds=meeting.duration_seconds,
            revision=meeting.transcript_revision,
            segments=[
                SegmentView(s.id, s.speaker_label, s.start_time, s.end_time, s.content)
                for s in segments
            ],
            executive_summary=summary.executive_summary if summary else None,
            key_points=list(summary.key_points) if summary else [],
            action_items=[
                ActionItemView(a.id, a.description, a.assignee, a.status) for a in items
            ],
        )
