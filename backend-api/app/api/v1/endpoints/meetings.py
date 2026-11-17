from fastapi import APIRouter, Query, status

from app.api.deps import (
    CurrentUser,
    MeetingForEdit,
    MeetingForManage,
    MeetingForView,
    MeetingServiceDep,
)
from app.schemas.meeting import (
    MeetingCreate,
    MeetingResponse,
    MeetingShareLinkResponse,
    MeetingUpdate,
)

router = APIRouter(prefix="/meetings", tags=["Meetings"])


@router.get("", response_model=list[MeetingResponse])
async def list_meetings(
    current_user: CurrentUser,
    service: MeetingServiceDep,
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[MeetingResponse]:
    """List the meetings visible to the authenticated user."""
    meetings = await service.list_meetings(
        user=current_user, search=search, status_filter=status_filter
    )
    return [MeetingResponse.model_validate(m) for m in meetings]


@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    payload: MeetingCreate, current_user: CurrentUser, service: MeetingServiceDep
) -> MeetingResponse:
    """Create a new meeting owned by the authenticated user."""
    meeting = await service.create_meeting(payload, user=current_user)
    return MeetingResponse.model_validate(meeting)


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(meeting: MeetingForView) -> MeetingResponse:
    """Retrieve meeting details (requires view access or a share token)."""
    return MeetingResponse.model_validate(meeting)


@router.patch("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    payload: MeetingUpdate, meeting: MeetingForEdit, service: MeetingServiceDep
) -> MeetingResponse:
    """Update the meeting title (requires edit access)."""
    return MeetingResponse.model_validate(await service.update_meeting(meeting, payload))


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting(meeting: MeetingForManage, service: MeetingServiceDep) -> None:
    """Soft delete a meeting (creator only)."""
    await service.soft_delete_meeting(meeting)


@router.post("/{meeting_id}/share", response_model=MeetingShareLinkResponse)
async def create_share_link(
    meeting: MeetingForManage,
    service: MeetingServiceDep,
    permission: str = Query(default="viewer", pattern="^(viewer|editor)$"),
) -> MeetingShareLinkResponse:
    """Create or update the share link of a meeting (creator only)."""
    return await service.generate_share_link(meeting, permission)
