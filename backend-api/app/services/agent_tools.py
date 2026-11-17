import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.actor import Actor
from app.domain.enums import Permission
from app.models.transcript import TranscriptSegmentModel
from app.schemas.agent import (
    AgentSegment,
    AgentSummaryResponse,
    OverviewResponse,
    SearchHit,
    SpeakerStat,
)
from app.services.access_policy import MeetingAccessPolicy
from app.services.retrieval_service import TranscriptRetriever
from app.services.summary_service import SummaryService

MAX_SEGMENTS = 200
MAX_MATCHES = 100


class AgentToolService:
    """Read-only operations the assistant may call, all authorized as the delegated user."""

    def __init__(
        self,
        session: AsyncSession,
        policy: MeetingAccessPolicy,
        retriever: TranscriptRetriever,
        summaries: SummaryService,
    ) -> None:
        """Initialize the service.

        Args:
            session: Active SQLAlchemy session.
            policy: Authorization seam.
            retriever: Hybrid transcript search.
            summaries: Summary and action item reads.
        """
        self.session = session
        self.policy = policy
        self.retriever = retriever
        self.summaries = summaries

    async def overview(self, actor: Actor, meeting_id: uuid.UUID) -> OverviewResponse:
        """Title, state, revision and per-speaker talk time of a meeting."""
        meeting = await self.policy.require(actor, meeting_id, Permission.VIEW)
        segments = await self._segments(meeting_id)
        stats: dict[str, SpeakerStat] = {}
        for segment in segments:
            stat = stats.setdefault(
                segment.speaker_label,
                SpeakerStat(speaker_label=segment.speaker_label, segments=0, talk_time_seconds=0.0),
            )
            stat.segments += 1
            stat.talk_time_seconds += max(0.0, segment.end_time - segment.start_time)
        return OverviewResponse(
            title=meeting.title,
            status=meeting.status,
            duration_seconds=meeting.duration_seconds,
            transcript_revision=meeting.transcript_revision,
            summary_status=meeting.summary_status,
            index_status=meeting.index_status,
            segments_count=len(segments),
            speakers=sorted(stats.values(), key=lambda s: -s.talk_time_seconds),
        )

    async def search(
        self, actor: Actor, meeting_id: uuid.UUID, query: str, k: int
    ) -> list[SearchHit]:
        """Hybrid search over the indexed transcript."""
        await self.policy.require(actor, meeting_id, Permission.VIEW)
        chunks = await self.retriever.search(meeting_id, query, k)
        return [
            SearchHit(
                chunk_id=c.id,
                speaker_label=c.speaker_label,
                start_time=c.start_time,
                end_time=c.end_time,
                text=c.text,
                segment_ids=c.segment_ids,
                score=c.score,
            )
            for c in chunks
        ]

    async def read_segments(
        self,
        actor: Actor,
        meeting_id: uuid.UUID,
        from_time: float | None,
        to_time: float | None,
        speaker: str | None,
        limit: int,
    ) -> list[AgentSegment]:
        """Read segments in a time window and/or of one speaker, capped at 200."""
        await self.policy.require(actor, meeting_id, Permission.VIEW)
        selected = [
            s
            for s in await self._segments(meeting_id)
            if (from_time is None or s.end_time >= from_time)
            and (to_time is None or s.start_time <= to_time)
            and (speaker is None or s.speaker_label == speaker)
        ]
        return [self._view(s) for s in selected[: min(limit, MAX_SEGMENTS)]]

    async def find_text(
        self, actor: Actor, meeting_id: uuid.UUID, pattern: str, case_sensitive: bool
    ) -> list[AgentSegment]:
        """Return segments containing the literal text, so edits can target exact ids."""
        await self.policy.require(actor, meeting_id, Permission.VIEW)
        regex = re.compile(re.escape(pattern), 0 if case_sensitive else re.IGNORECASE)
        matches = [s for s in await self._segments(meeting_id) if regex.search(s.content)]
        return [self._view(s) for s in matches[:MAX_MATCHES]]

    async def get_summary(self, actor: Actor, meeting_id: uuid.UUID) -> AgentSummaryResponse:
        """The generated summary, key points, and action items."""
        meeting = await self.policy.require(actor, meeting_id, Permission.VIEW)
        summary = await self.summaries.get_summary(meeting_id)
        items = await self.summaries.list_action_items(meeting_id)
        return AgentSummaryResponse(
            summary_status=meeting.summary_status,
            executive_summary=summary.executive_summary if summary else None,
            key_points=list(summary.key_points) if summary else [],
            action_items=[
                {
                    "id": str(i.id),
                    "description": i.description,
                    "assignee": i.assignee,
                    "status": i.status,
                    "due_date": i.due_date.isoformat() if i.due_date else None,
                }
                for i in items
            ],
        )

    async def _segments(self, meeting_id: uuid.UUID) -> list[TranscriptSegmentModel]:
        result = await self.session.scalars(
            select(TranscriptSegmentModel)
            .where(TranscriptSegmentModel.meeting_id == meeting_id)
            .order_by(TranscriptSegmentModel.sequence_order)
        )
        return list(result.all())

    @staticmethod
    def _view(segment: TranscriptSegmentModel) -> AgentSegment:
        return AgentSegment(
            segment_id=segment.id,
            speaker_label=segment.speaker_label,
            start_time=segment.start_time,
            end_time=segment.end_time,
            text=segment.content,
        )
