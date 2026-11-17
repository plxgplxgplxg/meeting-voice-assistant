import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.transcript import TranscriptSegmentModel
from app.schemas.transcript import TranscriptSegmentUpdate


class TranscriptService:
    """Service handling transcript reads and segment edits scoped to one meeting.

    Callers must authorize access to ``meeting_id`` first; every mutation here
    is additionally constrained to that meeting so a segment id can never be
    used to reach into another meeting.
    """

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

    async def get_segment_meeting_id(self, segment_id: uuid.UUID) -> uuid.UUID:
        """Resolve which meeting a segment belongs to.

        Args:
            segment_id: Segment identifier.

        Returns:
            Owning meeting id.

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

    async def update_segment(
        self, meeting_id: uuid.UUID, segment_id: uuid.UUID, payload: TranscriptSegmentUpdate
    ) -> TranscriptSegmentModel:
        """Update text content or speaker label of a segment in a meeting.

        Args:
            meeting_id: Meeting the segment must belong to.
            segment_id: Segment to update.
            payload: New content and/or speaker label.

        Returns:
            The updated segment.

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
        if payload.content is not None:
            segment.content = payload.content.strip()
        if payload.speaker_label is not None:
            segment.speaker_label = payload.speaker_label.strip()
        await self.session.flush()
        return segment

    async def bulk_rename_speaker(
        self, meeting_id: uuid.UUID, old_label: str, new_label: str
    ) -> int:
        """Rename a speaker across all segments in a meeting.

        Args:
            meeting_id: Target meeting UUID.
            old_label: Current speaker label string.
            new_label: Replacement speaker label string.

        Returns:
            Number of affected transcript segments.
        """
        result = await self.session.execute(
            update(TranscriptSegmentModel)
            .where(
                TranscriptSegmentModel.meeting_id == meeting_id,
                TranscriptSegmentModel.speaker_label == old_label.strip(),
            )
            .values(speaker_label=new_label.strip())
        )
        await self.session.flush()
        return result.rowcount or 0

    async def delete_segments(
        self, meeting_id: uuid.UUID, segment_ids: list[uuid.UUID]
    ) -> int:
        """Delete multiple segments from a meeting transcript.

        Args:
            meeting_id: Target meeting UUID.
            segment_ids: List of segment UUIDs to delete.

        Returns:
            Number of deleted segments.
        """
        result = await self.session.execute(
            delete(TranscriptSegmentModel).where(
                TranscriptSegmentModel.meeting_id == meeting_id,
                TranscriptSegmentModel.id.in_(segment_ids),
            )
        )
        await self.session.flush()
        return result.rowcount or 0
