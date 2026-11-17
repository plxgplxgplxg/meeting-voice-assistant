import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

MAX_OPERATIONS = 200


class UpdateText(BaseModel):
    """Replace the text of one segment."""

    op: Literal["update_text"] = "update_text"
    segment_id: uuid.UUID
    new_text: str = Field(min_length=1)


class ReplaceText(BaseModel):
    """Find and replace text across all segments or a chosen subset.

    Example: rename 'Gemany' to 'Gemini' everywhere.
    """

    op: Literal["replace_text"] = "replace_text"
    find: str = Field(min_length=1)
    replace: str
    scope: Literal["all", "segments"] = "all"
    segment_ids: list[uuid.UUID] | None = None
    case_sensitive: bool = False
    whole_word: bool = False


class RenameSpeaker(BaseModel):
    """Rename a speaker label in every segment that uses it."""

    op: Literal["rename_speaker"] = "rename_speaker"
    old_label: str = Field(min_length=1, max_length=100)
    new_label: str = Field(min_length=1, max_length=100)


class ReassignSpeaker(BaseModel):
    """Attribute specific segments to another speaker."""

    op: Literal["reassign_speaker"] = "reassign_speaker"
    segment_ids: list[uuid.UUID] = Field(min_length=1)
    new_label: str = Field(min_length=1, max_length=100)


class DeleteSegments(BaseModel):
    """Remove segments from the transcript."""

    op: Literal["delete_segments"] = "delete_segments"
    segment_ids: list[uuid.UUID] = Field(min_length=1)


class SplitSegment(BaseModel):
    """Split one segment into two at a character offset and a time."""

    op: Literal["split_segment"] = "split_segment"
    segment_id: uuid.UUID
    at_char: int = Field(ge=1)
    split_time: float = Field(ge=0)


class MergeSegments(BaseModel):
    """Merge adjacent segments of one speaker into the first of them."""

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


class OperationsRequest(BaseModel):
    """Batch of transcript operations applied as one change set."""

    operations: list[TranscriptOperation] = Field(min_length=1, max_length=MAX_OPERATIONS)
    expected_revision: int | None = Field(default=None, ge=0)
    reason: str | None = Field(default=None, max_length=500)


class OperationsPreviewRequest(BaseModel):
    """Batch of transcript operations to preview without writing."""

    operations: list[TranscriptOperation] = Field(min_length=1, max_length=MAX_OPERATIONS)


class SegmentDiffResponse(BaseModel):
    """Before and after state of one segment in a change set or preview."""

    op: Literal["update", "delete", "insert"]
    segment_id: uuid.UUID
    before: dict | None = None
    after: dict | None = None
    order_only: bool = False


class TranscriptDiffResponse(BaseModel):
    """Preview of what a batch of operations would change."""

    changes: list[SegmentDiffResponse]
    summary: str
    base_revision: int


class ChangeSetResultResponse(BaseModel):
    """Outcome of applying or reverting operations."""

    change_set_id: uuid.UUID
    revision: int
    affected_segment_ids: list[uuid.UUID]
    diff: TranscriptDiffResponse


class ChangeSetSummaryResponse(BaseModel):
    """One entry of the transcript history."""

    id: uuid.UUID
    revision: int
    actor_type: str
    actor_user_id: uuid.UUID | None = None
    summary: str
    reverts_change_set_id: uuid.UUID | None = None
    reverted: bool = False
    created_at: datetime


class ChangeSetDetailResponse(ChangeSetSummaryResponse):
    """History entry with its segment-level changes."""

    operations: list[dict]
    changes: list[SegmentDiffResponse]
