import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationFailedError
from app.models.summary import ActionItemModel, SummaryModel
from app.schemas.action_item_ops import (
    ActionItemOperation,
    CreateActionItem,
    DeleteActionItem,
    UpdateActionItem,
)
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

    async def preview_action_item_operations(
        self, meeting_id: uuid.UUID, operations: Sequence[ActionItemOperation]
    ) -> list[dict[str, Any]]:
        """Describe what operations would change without writing.

        Args:
            meeting_id: Meeting the operations target.
            operations: Operations to simulate.

        Returns:
            One entry per operation with ``op``, ``action_item_id``, ``before`` and ``after``.

        Raises:
            ValidationFailedError: If an operation references an unknown action item.
        """
        plan = await self._plan_action_item_operations(meeting_id, operations)
        return [entry for _, entry in plan]

    async def apply_action_item_operations(
        self, meeting_id: uuid.UUID, operations: Sequence[ActionItemOperation]
    ) -> list[dict[str, Any]]:
        """Apply operations. Items created here are user-owned, so regenerating the summary keeps them.

        Args:
            meeting_id: Meeting the operations target.
            operations: Operations to apply.

        Returns:
            The applied changes in the same shape as the preview.

        Raises:
            ValidationFailedError: If an operation references an unknown action item.
        """
        plan = await self._plan_action_item_operations(meeting_id, operations)
        by_id = {item.id: item for item in await self.list_action_items(meeting_id)}
        results: list[dict[str, Any]] = []
        for operation, entry in plan:
            if isinstance(operation, CreateActionItem):
                item = ActionItemModel(
                    meeting_id=meeting_id,
                    description=operation.description.strip(),
                    assignee=operation.assignee or "Unassigned",
                    due_date=operation.due_date,
                    status="pending",
                    source="user",
                )
                self.session.add(item)
                await self.session.flush()
                entry = {**entry, "action_item_id": str(item.id), "after": self._item_dict(item)}
            elif isinstance(operation, DeleteActionItem):
                await self.session.delete(by_id[operation.action_item_id])
            else:
                item = by_id[operation.action_item_id]
                for field in ("description", "assignee", "status", "due_date"):
                    value = getattr(operation, field)
                    if value is not None:
                        setattr(item, field, value)
                item.source = "user"
            results.append(entry)
        await self.session.flush()
        return results

    async def _plan_action_item_operations(
        self, meeting_id: uuid.UUID, operations: Sequence[ActionItemOperation]
    ) -> list[tuple[ActionItemOperation, dict[str, Any]]]:
        items = {item.id: item for item in await self.list_action_items(meeting_id)}
        plan: list[tuple[ActionItemOperation, dict[str, Any]]] = []
        for operation in operations:
            if isinstance(operation, CreateActionItem):
                after = {
                    "description": operation.description.strip(),
                    "assignee": operation.assignee or "Unassigned",
                    "status": "pending",
                    "due_date": operation.due_date.isoformat() if operation.due_date else None,
                }
                entry = {"op": "create", "action_item_id": None, "before": None, "after": after}
                plan.append((operation, entry))
                continue
            item = items.get(operation.action_item_id)
            if item is None:
                raise ValidationFailedError(
                    f"Action item {operation.action_item_id} does not exist in this meeting.",
                    code="ACTION_ITEM_NOT_FOUND",
                )
            before = self._item_dict(item)
            after = None
            if isinstance(operation, UpdateActionItem):
                after = {
                    **before,
                    **{
                        field: (
                            value.isoformat() if field == "due_date" and value is not None else value
                        )
                        for field in ("description", "assignee", "status", "due_date")
                        if (value := getattr(operation, field)) is not None
                    },
                }
            entry = {
                "op": operation.op,
                "action_item_id": str(item.id),
                "before": before,
                "after": after,
            }
            plan.append((operation, entry))
        return plan

    @staticmethod
    def _item_dict(item: ActionItemModel) -> dict[str, Any]:
        return {
            "description": item.description,
            "assignee": item.assignee,
            "status": item.status,
            "due_date": item.due_date.isoformat() if item.due_date else None,
        }
