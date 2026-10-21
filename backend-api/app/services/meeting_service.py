import uuid
from collections.abc import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meeting import MeetingModel
from app.schemas.meeting import MeetingCreate, MeetingUpdate


class MeetingService:
    """Service handling meeting entity operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_meetings(self) -> Sequence[MeetingModel]:
        """Retrieve all meetings ordered by creation date descending."""
        result = await self.session.execute(
            select(MeetingModel).order_by(MeetingModel.created_at.desc())
        )
        return result.scalars().all()

    async def get_meeting(self, meeting_id: uuid.UUID) -> MeetingModel | None:
        """Retrieve a specific meeting by ID."""
        return await self.session.get(MeetingModel, meeting_id)

    async def create_meeting(self, payload: MeetingCreate) -> MeetingModel:
        """Create a new meeting session."""
        meeting = MeetingModel(title=payload.title, status="created")
        self.session.add(meeting)
        await self.session.flush()
        return meeting

    async def update_meeting(
        self, meeting: MeetingModel, payload: MeetingUpdate
    ) -> MeetingModel:
        """Update an existing meeting."""
        if payload.title is not None:
            meeting.title = payload.title
        if payload.status is not None:
            meeting.status = payload.status
        self.session.add(meeting)
        await self.session.flush()
        return meeting
