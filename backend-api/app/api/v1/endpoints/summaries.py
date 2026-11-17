import uuid

from fastapi import APIRouter

from app.api.deps import (
    AccessPolicy,
    ActorDep,
    MeetingForEdit,
    MeetingForView,
    SummaryServiceDep,
)
from app.domain.enums import Permission
from app.schemas.summary import ActionItemResponse, ActionItemUpdate, SummaryResponse

router = APIRouter(tags=["Summaries"])
legacy_router = APIRouter(
    prefix="/summaries", tags=["Summaries (deprecated paths)"], deprecated=True
)


@router.get("/meetings/{meeting_id}/summary", response_model=SummaryResponse | None)
@legacy_router.get("/{meeting_id}", response_model=SummaryResponse | None)
async def get_meeting_summary(
    meeting: MeetingForView, service: SummaryServiceDep
) -> SummaryResponse | None:
    """Retrieve the AI generated summary for a meeting."""
    summary = await service.get_summary(meeting.id)
    return SummaryResponse.model_validate(summary) if summary else None


@router.get("/meetings/{meeting_id}/action-items", response_model=list[ActionItemResponse])
@legacy_router.get("/{meeting_id}/action-items", response_model=list[ActionItemResponse])
async def list_action_items(
    meeting: MeetingForView, service: SummaryServiceDep
) -> list[ActionItemResponse]:
    """Retrieve action items associated with a meeting."""
    items = await service.list_action_items(meeting.id)
    return [ActionItemResponse.model_validate(i) for i in items]


@router.patch(
    "/meetings/{meeting_id}/action-items/{action_item_id}", response_model=ActionItemResponse
)
async def update_action_item(
    action_item_id: uuid.UUID,
    payload: ActionItemUpdate,
    meeting: MeetingForEdit,
    service: SummaryServiceDep,
) -> ActionItemResponse:
    """Update status, assignee, or description of an action item."""
    item = await service.update_action_item(meeting.id, action_item_id, payload)
    return ActionItemResponse.model_validate(item)


@legacy_router.patch("/action-items/{action_item_id}", response_model=ActionItemResponse)
async def update_action_item_legacy(
    action_item_id: uuid.UUID,
    payload: ActionItemUpdate,
    actor: ActorDep,
    policy: AccessPolicy,
    service: SummaryServiceDep,
) -> ActionItemResponse:
    """Deprecated: update an action item without the meeting id in the path."""
    meeting_id = await service.get_action_item_meeting_id(action_item_id)
    meeting = await policy.require(actor, meeting_id, Permission.EDIT)
    item = await service.update_action_item(meeting.id, action_item_id, payload)
    return ActionItemResponse.model_validate(item)
