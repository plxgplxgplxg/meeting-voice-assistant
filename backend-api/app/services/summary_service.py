import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.summary import ActionItemModel, SummaryModel
from app.schemas.summary import ActionItemUpdate


class SummaryService:
    """Service reading summaries and editing action items scoped to one meeting.

    Callers must authorize access to ``meeting_id`` first.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_summary(self, meeting_id: uuid.UUID) -> SummaryModel | None:
        """Return the generated summary of a meeting, if one exists."""
        return await self.session.scalar(
            select(SummaryModel).where(SummaryModel.meeting_id == meeting_id)
        )

    async def list_action_items(self, meeting_id: uuid.UUID) -> list[ActionItemModel]:
        """List the action items of a meeting in creation order."""
        result = await self.session.execute(
            select(ActionItemModel)
            .where(ActionItemModel.meeting_id == meeting_id)
            .order_by(ActionItemModel.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_action_item_meeting_id(self, action_item_id: uuid.UUID) -> uuid.UUID:
        """Resolve which meeting an action item belongs to.

        Raises:
            NotFoundError: If the action item does not exist.
        """
        meeting_id = await self.session.scalar(
            select(ActionItemModel.meeting_id).where(ActionItemModel.id == action_item_id)
        )
        if meeting_id is None:
            raise NotFoundError("Action item not found.", code="ACTION_ITEM_NOT_FOUND")
        return meeting_id

    async def update_action_item(
        self, meeting_id: uuid.UUID, action_item_id: uuid.UUID, payload: ActionItemUpdate
    ) -> ActionItemModel:
        """Update status, assignee, or description of an action item.

        Args:
            meeting_id: Meeting the item must belong to.
            action_item_id: Item to update.
            payload: Fields to change.

        Returns:
            The updated action item.

        Raises:
            NotFoundError: If the item does not exist in this meeting.
        """
        item = await self.session.scalar(
            select(ActionItemModel).where(
                ActionItemModel.id == action_item_id,
                ActionItemModel.meeting_id == meeting_id,
            )
        )
        if item is None:
            raise NotFoundError("Action item not found.", code="ACTION_ITEM_NOT_FOUND")

        if payload.status is not None:
            item.status = payload.status
        if payload.assignee is not None:
            item.assignee = payload.assignee
        if payload.description is not None:
            item.description = payload.description
        await self.session.flush()
        return item
