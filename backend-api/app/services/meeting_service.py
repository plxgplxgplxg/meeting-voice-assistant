import secrets
import uuid
from collections.abc import Sequence
from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meeting import MeetingModel
from app.models.project import ProjectMeetingModel, ProjectMemberModel
from app.models.user import UserModel
from app.schemas.meeting import MeetingCreate, MeetingShareLinkResponse, MeetingUpdate


class MeetingService:
    """Service handling meeting session lifecycle, search, soft deletion, and share links."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_meetings(
        self,
        user: UserModel | None = None,
        search: str | None = None,
        status_filter: str | None = None,
        include_deleted: bool = False,
    ) -> Sequence[MeetingModel]:
        """List meetings filtered by access, search query, and status.

        Args:
            user: Optional authenticated user.
            search: Optional text filter for title.
            status_filter: Optional meeting status filter.
            include_deleted: Whether to return soft-deleted meetings.

        Returns:
            Sequence of MeetingModel instances.
        """
        query = select(MeetingModel)

        if not include_deleted:
            query = query.where(MeetingModel.is_deleted == False)

        if search:
            query = query.where(MeetingModel.title.ilike(f"%{search}%"))

        if status_filter:
            query = query.where(MeetingModel.status == status_filter)

        if user:
            # Accessible if user created it or user belongs to a project linked to the meeting
            accessible_project_ids = select(ProjectMemberModel.project_id).where(
                ProjectMemberModel.user_id == user.id
            )
            linked_meeting_ids = select(ProjectMeetingModel.meeting_id).where(
                ProjectMeetingModel.project_id.in_(accessible_project_ids)
            )
            query = query.where(
                or_(
                    MeetingModel.created_by == user.id,
                    MeetingModel.id.in_(linked_meeting_ids),
                )
            )

        query = query.order_by(MeetingModel.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_meeting(self, meeting_id: uuid.UUID) -> MeetingModel | None:
        """Retrieve a meeting by ID."""
        return await self.session.get(MeetingModel, meeting_id)

    async def create_meeting(
        self, payload: MeetingCreate, user: UserModel | None = None
    ) -> MeetingModel:
        """Create a new meeting session."""
        meeting = MeetingModel(
            title=payload.title,
            status="created",
            created_by=user.id if user else None,
        )
        self.session.add(meeting)
        await self.session.flush()
        return meeting

    async def update_meeting(
        self, meeting: MeetingModel, payload: MeetingUpdate
    ) -> MeetingModel:
        """Update meeting details."""
        if payload.title is not None:
            meeting.title = payload.title
        if payload.status is not None:
            meeting.status = payload.status
        self.session.add(meeting)
        await self.session.flush()
        return meeting

    async def soft_delete_meeting(
        self, meeting_id: uuid.UUID, user: UserModel
    ) -> None:
        """Soft delete a meeting (Creator only)."""
        meeting = await self.get_meeting(meeting_id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found."
            )
        if meeting.created_by and meeting.created_by != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the meeting creator can delete this meeting.",
            )
        meeting.is_deleted = True
        self.session.add(meeting)
        await self.session.flush()

    async def generate_share_link(
        self,
        meeting_id: uuid.UUID,
        permission: str,
        user: UserModel,
    ) -> MeetingShareLinkResponse:
        """Generate or update a public/token-protected shareable link."""
        meeting = await self.get_meeting(meeting_id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found."
            )
        if meeting.created_by and meeting.created_by != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the meeting creator can create share links.",
            )

        if not meeting.share_token:
            meeting.share_token = secrets.token_urlsafe(24)
        meeting.share_permission = permission
        self.session.add(meeting)
        await self.session.flush()

        return MeetingShareLinkResponse(
            meeting_id=meeting.id,
            share_token=meeting.share_token,
            share_url=f"/meetings/{meeting.id}?share={meeting.share_token}",
            share_permission=meeting.share_permission,
        )

    async def verify_meeting_access(
        self,
        meeting_id: uuid.UUID,
        user: UserModel | None,
        share_token: str | None,
        required_permission: str = "viewer",  # "viewer" or "editor"
    ) -> MeetingModel:
        """Verify user or guest token permission to access a meeting."""
        meeting = await self.get_meeting(meeting_id)
        if not meeting or meeting.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found."
            )

        # 1. Creator always has full editor access
        if user and meeting.created_by == user.id:
            return meeting

        # 2. Check project membership role
        if user:
            linked_project_ids = select(ProjectMeetingModel.project_id).where(
                ProjectMeetingModel.meeting_id == meeting.id
            )
            membership_result = await self.session.execute(
                select(ProjectMemberModel.role).where(
                    ProjectMemberModel.user_id == user.id,
                    ProjectMemberModel.project_id.in_(linked_project_ids),
                )
            )
            roles = set(membership_result.scalars().all())
            if "owner" in roles or "editor" in roles:
                return meeting
            if "viewer" in roles and required_permission == "viewer":
                return meeting

        # 3. Check share token
        if share_token and meeting.share_token == share_token:
            if required_permission == "editor" and meeting.share_permission != "editor":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Share link grants read-only viewer access.",
                )
            return meeting

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this meeting.",
        )
