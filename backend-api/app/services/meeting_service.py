import secrets
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationFailedError
from app.domain.enums import MeetingStatus, SharePermission
from app.models.meeting import MeetingModel
from app.models.user import UserModel
from app.schemas.meeting import MeetingCreate, MeetingShareLinkResponse, MeetingUpdate
from app.services.access_policy import MeetingAccessPolicy


class MeetingService:
    """Service handling meeting lifecycle, listing, soft deletion, and share links.

    Authorization is the caller's responsibility: endpoints resolve the target
    meeting through ``MeetingAccessPolicy`` before invoking mutations here.
    """

    def __init__(
        self,
        session: AsyncSession,
        access_policy: MeetingAccessPolicy | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            session: Active SQLAlchemy session.
            access_policy: Policy providing the visibility predicate.
        """
        self.session = session
        self.access_policy = access_policy or MeetingAccessPolicy(session)

    async def list_meetings(
        self,
        user: UserModel,
        search: str | None = None,
        status_filter: str | None = None,
    ) -> Sequence[MeetingModel]:
        """List the meetings visible to a user, newest first.

        Args:
            user: Authenticated user; only their meetings are returned.
            search: Optional case-insensitive title filter.
            status_filter: Optional meeting status filter.

        Returns:
            Visible, non-deleted meetings.
        """
        query = select(MeetingModel).where(
            MeetingModel.is_deleted.is_(False),
            self.access_policy.visible_meetings_clause(user.id),
        )
        if search:
            query = query.where(MeetingModel.title.ilike(f"%{search}%"))
        if status_filter:
            query = query.where(MeetingModel.status == status_filter)

        result = await self.session.execute(query.order_by(MeetingModel.created_at.desc()))
        return result.scalars().all()

    async def create_meeting(self, payload: MeetingCreate, user: UserModel) -> MeetingModel:
        """Create a new meeting owned by ``user``.

        Args:
            payload: Meeting attributes.
            user: Authenticated creator.

        Returns:
            Persisted meeting.
        """
        meeting = MeetingModel(
            title=payload.title, status=MeetingStatus.DRAFT, created_by=user.id
        )
        self.session.add(meeting)
        await self.session.flush()
        return meeting

    async def update_meeting(self, meeting: MeetingModel, payload: MeetingUpdate) -> MeetingModel:
        """Update client-editable meeting attributes.

        Args:
            meeting: Meeting already authorized for editing.
            payload: Fields to change. Status is system-managed and not accepted.

        Returns:
            The updated meeting.
        """
        if payload.title is not None:
            meeting.title = payload.title
        await self.session.flush()
        return meeting

    async def soft_delete_meeting(self, meeting: MeetingModel) -> None:
        """Soft delete a meeting already authorized for management."""
        meeting.is_deleted = True
        await self.session.flush()

    async def generate_share_link(
        self, meeting: MeetingModel, permission: str
    ) -> MeetingShareLinkResponse:
        """Create or update the share link of a meeting.

        Args:
            meeting: Meeting already authorized for management.
            permission: ``viewer`` or ``editor``.

        Returns:
            Share link details.

        Raises:
            ValidationFailedError: If the permission value is unknown.
        """
        if permission not in {p.value for p in SharePermission}:
            raise ValidationFailedError(f"Unknown share permission '{permission}'.")

        if not meeting.share_token:
            meeting.share_token = secrets.token_urlsafe(24)
        meeting.share_permission = permission
        await self.session.flush()

        return MeetingShareLinkResponse(
            meeting_id=meeting.id,
            share_token=meeting.share_token,
            share_url=f"/meetings/{meeting.id}?share={meeting.share_token}",
            share_permission=meeting.share_permission,
        )
