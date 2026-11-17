import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.meeting import MeetingResponse
from app.schemas.project import (
    AddProjectMemberRequest,
    ProjectCreateRequest,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdateRequest,
    UpdateProjectMemberRoleRequest,
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])



@router.get("", response_model=list[ProjectResponse])
async def list_my_projects(
    current_user: CurrentUser, db: DbSession
) -> list[ProjectResponse]:
    """List all workspace projects where current user is owner or member."""
    service = ProjectService(db)
    return await service.list_user_projects(current_user)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_new_project(
    payload: ProjectCreateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> ProjectResponse:
    """Create a new workspace project."""
    service = ProjectService(db)
    project = await service.create_project(current_user, payload)
    res = ProjectResponse.model_validate(project)
    res.my_role = "owner"
    return res


@router.get("/{project_id}")
async def get_project_details(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Retrieve detailed workspace information, member list, and linked meetings."""
    service = ProjectService(db)
    project, role, members, meetings = await service.get_project_detail(
        project_id, current_user
    )
    return {
        "project": ProjectResponse.model_validate(project),
        "my_role": role,
        "members": members,
        "meetings": [MeetingResponse.model_validate(m) for m in meetings],
    }


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project_info(
    project_id: uuid.UUID,
    payload: ProjectUpdateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> ProjectResponse:
    """Update workspace title and description (Owner only)."""
    service = ProjectService(db)
    updated = await service.update_project(project_id, current_user, payload)
    return ProjectResponse.model_validate(updated)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_workspace(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Delete a workspace project (Owner only)."""
    service = ProjectService(db)
    await service.delete_project(project_id, current_user)


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_project_member(
    project_id: uuid.UUID,
    payload: AddProjectMemberRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> ProjectMemberResponse:
    """Add a registered user to project by email (Owner or Editor)."""
    service = ProjectService(db)
    return await service.add_member(project_id, current_user, payload)


@router.patch("/{project_id}/members/{user_id}")
async def update_member_role(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: UpdateProjectMemberRoleRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> dict[str, str]:
    """Update access role of a project member (Owner only)."""
    service = ProjectService(db)
    await service.update_member_role(project_id, user_id, current_user, payload)
    return {"message": "Member role updated successfully."}


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Remove member from workspace (Owner only or self-leave)."""
    service = ProjectService(db)
    await service.remove_member(project_id, user_id, current_user)


@router.post("/{project_id}/meetings/{meeting_id}")
async def link_meeting_to_project(
    project_id: uuid.UUID,
    meeting_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict[str, str]:
    """Associate a meeting with this project workspace."""
    service = ProjectService(db)
    await service.add_meeting_to_project(project_id, meeting_id, current_user)
    return {"message": "Meeting successfully linked to project."}
