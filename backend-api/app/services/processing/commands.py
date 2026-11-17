import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidStateError
from app.domain.enums import IndexStatus, JobKind, MeetingStatus, SummaryStatus
from app.models.meeting import MeetingModel
from app.services.processing.jobs import JobService


class ProcessingCommands:
    """User-triggered commands that queue follow-up processing for a ready meeting.

    Callers must authorize EDIT access to the meeting first.
    """

    def __init__(self, session: AsyncSession, jobs: JobService) -> None:
        """Initialize the commands.

        Args:
            session: Active SQLAlchemy session.
            jobs: Job creation service.
        """
        self.session = session
        self.jobs = jobs

    async def request_reindex(self, meeting: MeetingModel) -> None:
        """Queue a rebuild of the retrieval index.

        Args:
            meeting: Meeting that is ready.

        Raises:
            InvalidStateError: If the meeting is not ready.
        """
        self._require_ready(meeting)
        meeting.index_status = IndexStatus.PENDING
        await self.jobs.enqueue(meeting.id, JobKind.INDEX, f"index:{meeting.id}:{uuid.uuid4().hex}")

    async def request_summary_regeneration(self, meeting: MeetingModel) -> None:
        """Queue a new summary and action item extraction from the current transcript.

        Args:
            meeting: Meeting that is ready.

        Raises:
            InvalidStateError: If the meeting is not ready.
        """
        self._require_ready(meeting)
        meeting.summary_status = SummaryStatus.PENDING
        await self.jobs.enqueue(
            meeting.id, JobKind.SUMMARIZE, f"summarize:{meeting.id}:{uuid.uuid4().hex}"
        )

    @staticmethod
    def _require_ready(meeting: MeetingModel) -> None:
        if meeting.status != MeetingStatus.READY:
            raise InvalidStateError(
                "The meeting must finish processing first.", code="INVALID_MEETING_STATE"
            )
