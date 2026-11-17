import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.transcript_ops import MAX_OPERATIONS


class CreateActionItem(BaseModel):
    """Add a new action item."""

    op: Literal["create"] = "create"
    description: str = Field(min_length=1, max_length=2000)
    assignee: str | None = Field(default=None, max_length=150)
    due_date: datetime | None = None


class UpdateActionItem(BaseModel):
    """Change fields of an existing action item."""

    op: Literal["update"] = "update"
    action_item_id: uuid.UUID
    description: str | None = Field(default=None, min_length=1, max_length=2000)
    assignee: str | None = Field(default=None, max_length=150)
    status: Literal["pending", "completed"] | None = None
    due_date: datetime | None = None


class DeleteActionItem(BaseModel):
    """Remove an action item."""

    op: Literal["delete"] = "delete"
    action_item_id: uuid.UUID


ActionItemOperation = Annotated[
    CreateActionItem | UpdateActionItem | DeleteActionItem, Field(discriminator="op")
]

MAX_ACTION_ITEM_OPERATIONS = MAX_OPERATIONS
