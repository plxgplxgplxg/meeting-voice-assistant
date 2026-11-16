import uuid
from collections.abc import Sequence
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transcript import TranscriptSegmentModel
from app.schemas.transcript import TranscriptSegmentUpdate


class TranscriptService:
    """Service handling meeting transcript operations, segment editing, and speaker renaming."""

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
            segment.content = payload.content.strip()
        if payload.speaker_label is not None:
            segment.speaker_label = payload.speaker_label.strip()
        self.session.add(segment)
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
        stmt = (
            update(TranscriptSegmentModel)
            .where(
                TranscriptSegmentModel.meeting_id == meeting_id,
                TranscriptSegmentModel.speaker_label == old_label.strip(),
            )
            .values(speaker_label=new_label.strip())
        )
        result = await self.session.execute(stmt)
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
        stmt = delete(TranscriptSegmentModel).where(
            TranscriptSegmentModel.meeting_id == meeting_id,
            TranscriptSegmentModel.id.in_(segment_ids),
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount or 0
