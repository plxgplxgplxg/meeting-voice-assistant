import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.summary import ActionItemModel, SummaryModel
from app.schemas.summary import ActionItemResponse, ActionItemUpdate, SummaryResponse

router = APIRouter(prefix="/summaries", tags=["Summaries"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/{meeting_id}", response_model=SummaryResponse | None)
async def get_meeting_summary(
    meeting_id: uuid.UUID, db: DatabaseSession
) -> SummaryResponse | None:
    """Retrieve the AI generated summary for a meeting."""
    result = await db.execute(
        select(SummaryModel).where(SummaryModel.meeting_id == meeting_id)
    )
    summary = result.scalar_one_or_none()
    return SummaryResponse.model_validate(summary) if summary else None


@router.get("/{meeting_id}/action-items", response_model=list[ActionItemResponse])
async def list_action_items(
    meeting_id: uuid.UUID, db: DatabaseSession
) -> list[ActionItemResponse]:
    """Retrieve action items associated with a meeting."""
    result = await db.execute(
        select(ActionItemModel)
        .where(ActionItemModel.meeting_id == meeting_id)
        .order_by(ActionItemModel.created_at.asc())
    )
    items = result.scalars().all()
    return [ActionItemResponse.model_validate(i) for i in items]


@router.patch("/action-items/{action_item_id}", response_model=ActionItemResponse)
async def update_action_item(
    action_item_id: uuid.UUID,
    payload: ActionItemUpdate,
    db: DatabaseSession,
) -> ActionItemResponse:
    """Update status or assignee of an action item."""
    item = await db.get(ActionItemModel, action_item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action item with ID '{action_item_id}' not found.",
        )

    if payload.status is not None:
        item.status = payload.status
    if payload.assignee is not None:
        item.assignee = payload.assignee
    if payload.description is not None:
        item.description = payload.description

    db.add(item)
    await db.commit()
    return ActionItemResponse.model_validate(item)
