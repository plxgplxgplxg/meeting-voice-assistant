import uuid
from collections.abc import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transcript import TranscriptSegmentModel
from app.schemas.transcript import TranscriptSegmentUpdate


class TranscriptService:
    """Service handling meeting transcript operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_segments_by_meeting(
        self, meeting_id: uuid.UUID
    ) -> Sequence[TranscriptSegmentModel]:
        """Retrieve transcript segments for a meeting in chronological order."""
        result = await self.session.execute(
            select(TranscriptSegmentModel)
            .where(TranscriptSegmentModel.meeting_id == meeting_id)
            .order_by(TranscriptSegmentModel.sequence_order.asc())
        )
        return result.scalars().all()

    async def update_segment(
        self, segment_id: uuid.UUID, payload: TranscriptSegmentUpdate
    ) -> TranscriptSegmentModel | None:
        """Update text content or speaker label of a specific segment."""
        segment = await self.session.get(TranscriptSegmentModel, segment_id)
        if not segment:
            return None
        if payload.content is not None:
            segment.content = payload.content
        if payload.speaker_label is not None:
            segment.speaker_label = payload.speaker_label
        self.session.add(segment)
        await self.session.flush()
        return segment
