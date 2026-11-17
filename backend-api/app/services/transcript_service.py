import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.transcript import TranscriptSegmentModel


class TranscriptService:
    """Read-side access to transcripts. Every mutation goes through ``TranscriptEditor``."""

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

    async def get_segment(
        self, meeting_id: uuid.UUID, segment_id: uuid.UUID
    ) -> TranscriptSegmentModel:
        """Return one segment of a meeting.

        Raises:
            NotFoundError: If the segment does not exist in this meeting.
        """
        segment = await self.session.scalar(
            select(TranscriptSegmentModel).where(
                TranscriptSegmentModel.id == segment_id,
                TranscriptSegmentModel.meeting_id == meeting_id,
            )
        )
        if segment is None:
            raise NotFoundError("Transcript segment not found.", code="SEGMENT_NOT_FOUND")
        return segment

    async def get_segment_meeting_id(self, segment_id: uuid.UUID) -> uuid.UUID:
        """Resolve which meeting a segment belongs to.

        Raises:
            NotFoundError: If the segment does not exist.
        """
        meeting_id = await self.session.scalar(
            select(TranscriptSegmentModel.meeting_id).where(
                TranscriptSegmentModel.id == segment_id
            )
        )
        if meeting_id is None:
            raise NotFoundError("Transcript segment not found.", code="SEGMENT_NOT_FOUND")
        return meeting_id
