import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, Field

MAX_PROPOSAL_OPERATIONS = 200


class UpdateText(BaseModel):
    """Replace the whole text of one segment."""

    op: Literal["update_text"] = "update_text"
    segment_id: uuid.UUID
    new_text: str = Field(min_length=1)


class ReplaceText(BaseModel):
    """Find and replace text in all segments, or only in the listed ones."""

    op: Literal["replace_text"] = "replace_text"
    find: str = Field(min_length=1)
    replace: str
    scope: Literal["all", "segments"] = "all"
    segment_ids: list[uuid.UUID] | None = None
    case_sensitive: bool = False
    whole_word: bool = False


class RenameSpeaker(BaseModel):
    """Rename a speaker label everywhere it appears."""

    op: Literal["rename_speaker"] = "rename_speaker"
    old_label: str = Field(min_length=1, max_length=100)
    new_label: str = Field(min_length=1, max_length=100)


class ReassignSpeaker(BaseModel):
    """Attribute specific segments to a different speaker."""

    op: Literal["reassign_speaker"] = "reassign_speaker"
    segment_ids: list[uuid.UUID] = Field(min_length=1)
    new_label: str = Field(min_length=1, max_length=100)


class DeleteSegments(BaseModel):
    """Delete segments, for example greetings at the start of the meeting."""

    op: Literal["delete_segments"] = "delete_segments"
    segment_ids: list[uuid.UUID] = Field(min_length=1)


class SplitSegment(BaseModel):
    """Split one segment into two at a character offset and a timestamp."""

    op: Literal["split_segment"] = "split_segment"
    segment_id: uuid.UUID
    at_char: int = Field(ge=1)
    split_time: float = Field(ge=0)


class MergeSegments(BaseModel):
    """Merge adjacent segments of the same speaker."""

    op: Literal["merge_segments"] = "merge_segments"
    segment_ids: list[uuid.UUID] = Field(min_length=2)


TranscriptOperation = Annotated[
    UpdateText
    | ReplaceText
    | RenameSpeaker
    | ReassignSpeaker
    | DeleteSegments
    | SplitSegment
    | MergeSegments,
    Field(discriminator="op"),
]


class CreateActionItem(BaseModel):
    """Add an action item."""

    op: Literal["create"] = "create"
    description: str = Field(min_length=1, max_length=2000)
    assignee: str | None = None
    due_date: str | None = Field(default=None, description="ISO 8601 date or datetime")


class UpdateActionItem(BaseModel):
    """Change an existing action item."""

    op: Literal["update"] = "update"
    action_item_id: uuid.UUID
    description: str | None = None
    assignee: str | None = None
    status: Literal["pending", "completed"] | None = None
    due_date: str | None = None


class DeleteActionItem(BaseModel):
    """Remove an action item."""

    op: Literal["delete"] = "delete"
    action_item_id: uuid.UUID


ActionItemOperation = Annotated[
    CreateActionItem | UpdateActionItem | DeleteActionItem, Field(discriminator="op")
]
