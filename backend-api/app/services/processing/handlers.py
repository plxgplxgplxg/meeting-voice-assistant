from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import IndexStatus, JobKind, SummaryStatus
from app.domain.events import TranscriptEdited, TranscriptReplaced
from app.models.meeting import MeetingModel
from app.services.processing.jobs import JobService

EDIT_REINDEX_DELAY_SECONDS = 3.0


class TranscriptEventHandlers:
    """Keeps derived data (summary, retrieval index) consistent with the transcript."""

    def __init__(self, session: AsyncSession, jobs: JobService) -> None:
        """Initialize the handlers.

        Args:
            session: Session of the publishing transaction.
            jobs: Creates follow-up jobs through the outbox.
        """
        self.session = session
        self.jobs = jobs

    async def on_edited(self, event: TranscriptEdited) -> None:
        """Mark derived data stale after an edit and queue a debounced re-index.

        The summary is never regenerated automatically; the UI offers a manual
        regenerate. The index job is delayed a few seconds and keyed by revision,
        and the index step always rebuilds from the latest transcript, so a burst
        of edits collapses into one effective rebuild.

        Args:
            event: The edit that happened.
        """
        meeting = await self.session.get(MeetingModel, event.meeting_id)
        if meeting is None:
            return
        if meeting.summary_status == SummaryStatus.READY:
            meeting.summary_status = SummaryStatus.STALE
        if meeting.index_status == IndexStatus.READY:
            meeting.index_status = IndexStatus.STALE
            await self.jobs.enqueue(
                meeting.id,
                JobKind.INDEX,
                f"index:{meeting.id}:{event.revision}",
                delay_seconds=EDIT_REINDEX_DELAY_SECONDS,
            )

    async def on_replaced(self, event: TranscriptReplaced) -> None:
        """Queue summarization and indexing after a fresh transcription.

        Args:
            event: The replacement that happened.
        """
        meeting = await self.session.get(MeetingModel, event.meeting_id)
        if meeting is None:
            return
        meeting.summary_status = SummaryStatus.PENDING
        meeting.index_status = IndexStatus.PENDING
        await self.jobs.enqueue(
            meeting.id,
            JobKind.SUMMARIZE,
            f"summarize:{meeting.id}:{event.revision}",
            event.audio_file_id,
        )
        await self.jobs.enqueue(
            meeting.id,
            JobKind.INDEX,
            f"index:{meeting.id}:{event.revision}",
            event.audio_file_id,
        )
