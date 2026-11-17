import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.action_item_ops import MAX_ACTION_ITEM_OPERATIONS, ActionItemOperation
from app.schemas.transcript_ops import MAX_OPERATIONS, TranscriptOperation

ActionKind = Literal["transcript_ops", "action_item_ops", "summary_regenerate"]
ActionStatus = Literal["proposed", "approved", "rejected", "applied", "failed", "expired"]
ArtifactKindLiteral = Literal["minutes_docx", "email_draft", "srt", "custom_md"]


class ProposalRequest(BaseModel):
    """A change the assistant wants to make, stored until the user decides."""

    kind: ActionKind
    base_revision: int = Field(ge=0)
    operations: list[TranscriptOperation] | None = Field(default=None, max_length=MAX_OPERATIONS)
    action_item_operations: list[ActionItemOperation] | None = Field(
        default=None, max_length=MAX_ACTION_ITEM_OPERATIONS
    )


class ApproveRequest(BaseModel):
    """Optional user edits applied to the proposal before it runs."""

    operations: list[TranscriptOperation] | None = Field(default=None, max_length=MAX_OPERATIONS)
    action_item_operations: list[ActionItemOperation] | None = Field(
        default=None, max_length=MAX_ACTION_ITEM_OPERATIONS
    )


class AgentActionResponse(BaseModel):
    """A proposal and its outcome."""

    id: uuid.UUID
    conversation_id: uuid.UUID
    meeting_id: uuid.UUID
    kind: str
    status: str
    base_revision: int
    payload: dict[str, Any]
    preview: dict[str, Any]
    result: dict[str, Any] | None = None
    change_set_id: uuid.UUID | None = None
    created_at: datetime
    decided_at: datetime | None = None

    model_config = {"from_attributes": True}


class TurnRequest(BaseModel):
    """A message to the meeting assistant."""

    message: str = Field(min_length=1, max_length=4000)


class SpeakerStat(BaseModel):
    """Talk time of one speaker."""

    speaker_label: str
    segments: int
    talk_time_seconds: float


class OverviewResponse(BaseModel):
    """Compact facts about a meeting for the agent's first look."""

    title: str
    status: str
    duration_seconds: float
    transcript_revision: int
    summary_status: str
    index_status: str
    segments_count: int
    speakers: list[SpeakerStat]


class SearchRequest(BaseModel):
    """Hybrid search over a meeting's transcript."""

    query: str = Field(min_length=1, max_length=1000)
    k: int = Field(default=5, ge=1, le=10)


class AgentSegment(BaseModel):
    """A transcript segment as shown to the agent."""

    segment_id: uuid.UUID
    speaker_label: str
    start_time: float
    end_time: float
    text: str


class SearchHit(BaseModel):
    """A retrieved chunk of the transcript."""

    chunk_id: uuid.UUID
    speaker_label: str
    start_time: float
    end_time: float
    text: str
    segment_ids: list[uuid.UUID]
    score: float


class FindRequest(BaseModel):
    """Literal text search returning the segments that contain it."""

    pattern: str = Field(min_length=1, max_length=200)
    case_sensitive: bool = False


class AgentSummaryResponse(BaseModel):
    """Summary and action items for the agent."""

    summary_status: str
    executive_summary: str | None = None
    key_points: list[Any] = Field(default_factory=list)
    action_items: list[dict[str, Any]] = Field(default_factory=list)


class ArtifactCreateRequest(BaseModel):
    """Request to generate a document for a meeting."""

    kind: ArtifactKindLiteral
    title: str = Field(min_length=1, max_length=255)
    content_markdown: str | None = None


class ArtifactResponse(BaseModel):
    """A generated document."""

    id: uuid.UUID
    meeting_id: uuid.UUID
    kind: str
    title: str
    mime_type: str
    size_bytes: int
    source_revision: int
    created_at: datetime

    model_config = {"from_attributes": True}
