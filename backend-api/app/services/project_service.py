import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    ConflictError,
    InvalidStateError,
    NotFoundError,
    PermissionDeniedError,
)
from app.domain.actor import Actor
from app.domain.enums import Permission, ProjectRole
from app.models.meeting import MeetingModel
from app.models.project import ProjectMeetingModel, ProjectMemberModel, ProjectModel
from app.models.user import UserModel
from app.schemas.project import (
    AddProjectMemberRequest,
    ProjectCreateRequest,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdateRequest,
    UpdateProjectMemberRoleRequest,
)
from app.services.access_policy import MeetingAccessPolicy


class ProjectService:
    """Service handling workspace projects, member authorization, and meeting links."""

    def __init__(
        self,
        session: AsyncSession,
        access_policy: MeetingAccessPolicy | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            session: Active SQLAlchemy session.
            access_policy: Policy used to authorize access to meetings being linked.
        """
        self.session = session
        self.access_policy = access_policy or MeetingAccessPolicy(session)

    async def create_project(
        self, user: UserModel, payload: ProjectCreateRequest
    ) -> ProjectModel:
        """Create a new project workspace and register creator as owner."""
        project = ProjectModel(
            name=payload.name,
            description=payload.description,
            owner_id=user.id,
        )
        self.session.add(project)
        await self.session.flush()

        member = ProjectMemberModel(
            project_id=project.id,
            user_id=user.id,
            role="owner",
        )
        self.session.add(member)
        await self.session.flush()
        return project

    async def list_user_projects(self, user: UserModel) -> list[ProjectResponse]:
        """List all projects where user is owner or member with counts."""
        subquery = (
            select(ProjectMemberModel.project_id, ProjectMemberModel.role)
            .where(ProjectMemberModel.user_id == user.id)
            .subquery()
        )

        query = (
            select(
                ProjectModel,
                subquery.c.role,
                func.count(func.distinct(ProjectMemberModel.id)).label("members_count"),
                func.count(func.distinct(ProjectMeetingModel.id)).label("meetings_count"),
            )
            .join(subquery, ProjectModel.id == subquery.c.project_id)
            .outerjoin(ProjectMemberModel, ProjectModel.id == ProjectMemberModel.project_id)
            .outerjoin(ProjectMeetingModel, ProjectModel.id == ProjectMeetingModel.project_id)
            .group_by(ProjectModel.id, subquery.c.role)
            .order_by(ProjectModel.created_at.desc())
        )

        result = await self.session.execute(query)
        rows = result.all()

        responses = []
        for project, my_role, members_count, meetings_count in rows:
            res = ProjectResponse.model_validate(project)
            res.my_role = my_role
            res.members_count = members_count
            res.meetings_count = meetings_count
            responses.append(res)

        return responses

    async def get_project_detail(
        self, project_id: uuid.UUID, user: UserModel
    ) -> tuple[ProjectModel, str, list[ProjectMemberResponse], list[MeetingModel]]:
        """Retrieve project with authorized member check, member list, and linked meetings."""
        membership = await self._get_membership(project_id, user.id)
        if not membership:
            raise PermissionDeniedError("You do not have access to this project.")

        project = await self.session.get(ProjectModel, project_id)
        if not project:
            raise NotFoundError("Project not found.")

        # Get members with user profiles
        members_query = (
            select(ProjectMemberModel, UserModel)
            .join(UserModel, ProjectMemberModel.user_id == UserModel.id)
            .where(ProjectMemberModel.project_id == project_id)
            .order_by(ProjectMemberModel.created_at.asc())
        )
        members_result = await self.session.execute(members_query)
        member_responses = [
            ProjectMemberResponse(
                id=pm.id,
                user_id=u.id,
                email=u.email,
                full_name=u.full_name,
                role=pm.role,
                created_at=pm.created_at,
            )
            for pm, u in members_result.all()
        ]

        # Get linked meetings
        meetings_query = (
            select(MeetingModel)
            .join(ProjectMeetingModel, MeetingModel.id == ProjectMeetingModel.meeting_id)
            .where(
                ProjectMeetingModel.project_id == project_id,
                MeetingModel.is_deleted.is_(False),
            )
            .order_by(MeetingModel.created_at.desc())
        )
        meetings_result = await self.session.execute(meetings_query)
        meetings = list(meetings_result.scalars().all())

        return project, membership.role, member_responses, meetings

    async def update_project(
        self, project_id: uuid.UUID, user: UserModel, payload: ProjectUpdateRequest
    ) -> ProjectModel:
        """Update project details (owner only)."""
        project = await self._ensure_owner(project_id, user.id)
        if payload.name is not None:
            project.name = payload.name
        if payload.description is not None:
            project.description = payload.description

        self.session.add(project)
        await self.session.flush()
        return project

    async def delete_project(self, project_id: uuid.UUID, user: UserModel) -> None:
        """Delete project workspace (owner only)."""
        project = await self._ensure_owner(project_id, user.id)
        await self.session.delete(project)
        await self.session.flush()

    async def add_member(
        self, project_id: uuid.UUID, user: UserModel, payload: AddProjectMemberRequest
    ) -> ProjectMemberResponse:
        """Add a registered user to project by email (owner or editor)."""
        await self._ensure_role(project_id, user.id, {ProjectRole.OWNER, ProjectRole.EDITOR})

        target_user = await self.session.scalar(
            select(UserModel).where(UserModel.email == payload.email)
        )
        if not target_user:
            raise NotFoundError(f"User with email '{payload.email}' not found.")

        existing = await self._get_membership(project_id, target_user.id)
        if existing:
            raise ConflictError("User is already a member of this project.")

        member = ProjectMemberModel(
            project_id=project_id,
            user_id=target_user.id,
            role=payload.role,
        )
        self.session.add(member)
        await self.session.flush()

        return ProjectMemberResponse(
            id=member.id,
            user_id=target_user.id,
            email=target_user.email,
            full_name=target_user.full_name,
            role=member.role,
            created_at=member.created_at,
        )

    async def update_member_role(
        self,
        project_id: uuid.UUID,
        target_user_id: uuid.UUID,
        user: UserModel,
        payload: UpdateProjectMemberRoleRequest,
    ) -> ProjectMemberModel:
        """Update a member's role (owner only)."""
        await self._ensure_owner(project_id, user.id)

        member = await self._get_membership(project_id, target_user_id)
        if not member:
            raise NotFoundError("Member not found.")
        if member.role == "owner":
            raise InvalidStateError("Cannot modify project owner role.")

        member.role = payload.role
        self.session.add(member)
        await self.session.flush()
        return member

    async def remove_member(
        self, project_id: uuid.UUID, target_user_id: uuid.UUID, user: UserModel
    ) -> None:
        """Remove a member from project (owner only, or member leaving)."""
        is_self_leaving = target_user_id == user.id
        if not is_self_leaving:
            await self._ensure_owner(project_id, user.id)

        member = await self._get_membership(project_id, target_user_id)
        if not member:
            raise NotFoundError("Member not found.")
        if member.role == "owner":
            raise InvalidStateError("Owner cannot be removed from project.")

        await self.session.delete(member)
        await self.session.flush()

    async def add_meeting_to_project(
        self, project_id: uuid.UUID, meeting_id: uuid.UUID, user: UserModel
    ) -> ProjectMeetingModel:
        """Link an existing meeting to a project.

        The caller must be an owner or editor of the project and must also hold
        EDIT access to the meeting, otherwise any project editor could pull an
        arbitrary meeting into their workspace and gain access to it.

        Args:
            project_id: Target project.
            meeting_id: Meeting to link.
            user: Authenticated caller.

        Returns:
            Existing or newly created link.

        Raises:
            PermissionDeniedError: If the caller lacks project or meeting rights.
            NotFoundError: If the meeting does not exist.
        """
        await self._ensure_role(project_id, user.id, {ProjectRole.OWNER, ProjectRole.EDITOR})
        await self.access_policy.require(Actor(user_id=user.id), meeting_id, Permission.EDIT)

        existing = await self.session.scalar(
            select(ProjectMeetingModel).where(
                ProjectMeetingModel.project_id == project_id,
                ProjectMeetingModel.meeting_id == meeting_id,
            )
        )
        if existing:
            return existing

        link = ProjectMeetingModel(
            project_id=project_id,
            meeting_id=meeting_id,
            added_by=user.id,
        )
        self.session.add(link)
        await self.session.flush()
        return link

    async def _get_membership(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> ProjectMemberModel | None:
        return await self.session.scalar(
            select(ProjectMemberModel).where(
                ProjectMemberModel.project_id == project_id,
                ProjectMemberModel.user_id == user_id,
            )
        )

    async def _ensure_owner(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> ProjectModel:
        project = await self.session.get(ProjectModel, project_id)
        if not project:
            raise NotFoundError("Project not found.")
        if project.owner_id != user_id:
            raise PermissionDeniedError("Only project owner can perform this operation.")
        return project

    async def _ensure_role(
        self, project_id: uuid.UUID, user_id: uuid.UUID, allowed_roles: set[str]
    ) -> ProjectMemberModel:
        membership = await self._get_membership(project_id, user_id)
        if not membership or membership.role not in allowed_roles:
            raise PermissionDeniedError("Insufficient permissions for this project operation.")
        return membership
