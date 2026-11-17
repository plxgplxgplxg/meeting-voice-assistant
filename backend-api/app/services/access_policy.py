import secrets
import uuid

from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, PermissionDeniedError
from app.domain.actor import Actor
from app.domain.enums import PERMISSION_RANK, Permission, ProjectRole, SharePermission
from app.models.meeting import MeetingModel
from app.models.project import ProjectMeetingModel, ProjectMemberModel


class MeetingAccessPolicy:
    """Single authority deciding what an actor may do with a meeting.

    Rules (highest granted permission wins):

    - Creator: MANAGE (delete, share). Legacy meetings without a creator can
      never be managed.
    - Project owner or editor of a linked project: EDIT. Project viewer: VIEW.
    - Share token: VIEW or EDIT according to the meeting's share permission,
      never MANAGE. Agents cannot use share tokens.
    - Soft-deleted meetings do not exist for anyone.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the policy.

        Args:
            session: Active SQLAlchemy session used for meeting and membership lookups.
        """
        self.session = session

    async def require(
        self, actor: Actor, meeting_id: uuid.UUID, permission: Permission
    ) -> MeetingModel:
        """Load a meeting and verify the actor holds at least ``permission``.

        Args:
            actor: Identity performing the operation.
            meeting_id: Meeting being accessed.
            permission: Minimum permission required.

        Returns:
            The loaded meeting.

        Raises:
            NotFoundError: If the meeting does not exist or is soft-deleted.
            PermissionDeniedError: If the actor lacks the required permission.
        """
        meeting = await self.session.get(MeetingModel, meeting_id)
        if not meeting or meeting.is_deleted:
            raise NotFoundError("Meeting not found.", code="MEETING_NOT_FOUND")

        granted = await self.granted_permission(actor, meeting)
        if granted is None:
            raise PermissionDeniedError(
                "You do not have permission to access this meeting.", code="MEETING_FORBIDDEN"
            )
        if PERMISSION_RANK[granted] < PERMISSION_RANK[permission]:
            raise PermissionDeniedError(
                f"This action requires '{permission}' access to the meeting.",
                code="MEETING_FORBIDDEN",
            )
        return meeting

    async def require_existing(self, meeting_id: uuid.UUID) -> MeetingModel:
        """Load a meeting without checking the caller, for pre-authorized access.

        Only use this when access was already proven another way, such as a
        valid signed URL.

        Args:
            meeting_id: Meeting being accessed.

        Returns:
            The loaded meeting.

        Raises:
            NotFoundError: If the meeting does not exist or is soft-deleted.
        """
        meeting = await self.session.get(MeetingModel, meeting_id)
        if not meeting or meeting.is_deleted:
            raise NotFoundError("Meeting not found.", code="MEETING_NOT_FOUND")
        return meeting

    async def granted_permission(
        self, actor: Actor, meeting: MeetingModel
    ) -> Permission | None:
        """Compute the highest permission the actor holds on a meeting.

        Args:
            actor: Identity performing the operation.
            meeting: Loaded meeting.

        Returns:
            The highest granted permission, or None when the actor has no access.
        """
        grants: list[Permission] = []

        if actor.user_id is not None:
            if meeting.created_by == actor.user_id:
                grants.append(Permission.MANAGE)
            else:
                grants.extend(await self._project_grants(actor.user_id, meeting.id))

        if self._share_token_matches(actor, meeting):
            grants.append(
                Permission.EDIT
                if meeting.share_permission == SharePermission.EDITOR
                else Permission.VIEW
            )

        return max(grants, key=PERMISSION_RANK.__getitem__, default=None)

    def visible_meetings_clause(self, user_id: uuid.UUID) -> ColumnElement[bool]:
        """Build the SQL predicate selecting meetings a user can at least view.

        Args:
            user_id: Authenticated user.

        Returns:
            Clause matching meetings the user created or reaches through a project.
        """
        member_projects = select(ProjectMemberModel.project_id).where(
            ProjectMemberModel.user_id == user_id
        )
        linked_meetings = select(ProjectMeetingModel.meeting_id).where(
            ProjectMeetingModel.project_id.in_(member_projects)
        )
        return or_(MeetingModel.created_by == user_id, MeetingModel.id.in_(linked_meetings))

    async def _project_grants(
        self, user_id: uuid.UUID, meeting_id: uuid.UUID
    ) -> list[Permission]:
        linked_projects = select(ProjectMeetingModel.project_id).where(
            ProjectMeetingModel.meeting_id == meeting_id
        )
        roles = set(
            await self.session.scalars(
                select(ProjectMemberModel.role).where(
                    ProjectMemberModel.user_id == user_id,
                    ProjectMemberModel.project_id.in_(linked_projects),
                )
            )
        )
        grants: list[Permission] = []
        if roles & {ProjectRole.OWNER, ProjectRole.EDITOR}:
            grants.append(Permission.EDIT)
        if ProjectRole.VIEWER in roles:
            grants.append(Permission.VIEW)
        return grants

    @staticmethod
    def _share_token_matches(actor: Actor, meeting: MeetingModel) -> bool:
        if actor.via == "agent" or not actor.share_token or not meeting.share_token:
            return False
        return secrets.compare_digest(
            actor.share_token.encode(), meeting.share_token.encode()
        )
