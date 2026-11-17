import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utc_now
from app.core.database import Base
from app.models.constraints import enum_check
from app.models.types import UTCDateTime


class TranscriptChangeSetModel(Base):
    """One atomic edit of a meeting transcript, the unit of history and undo.

    ``operations`` keeps the logical operations (split, merge, replace, ...) that
    produced the segment-level changes, for audit and for the history view.
    """
    __tablename__ = "transcript_change_sets"
    __table_args__ = (
        UniqueConstraint("meeting_id", "revision"),
        enum_check("actor_type", ("user", "agent", "system"), "actor_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    actor_type: Mapped[str] = mapped_column(String(10), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reverts_change_set_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transcript_change_sets.id", ondelete="SET NULL"),
        nullable=True,
    )
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    operations: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, server_default=func.now(), nullable=False
    )

    changes = relationship(
        "TranscriptSegmentChangeModel", back_populates="change_set", cascade="all, delete-orphan"
    )


class TranscriptSegmentChangeModel(Base):
    """Before and after snapshot of one segment within a change set."""
    __tablename__ = "transcript_segment_changes"
    __table_args__ = (enum_check("op", ("update", "delete", "insert"), "op"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    change_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transcript_change_sets.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    segment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    op: Mapped[str] = mapped_column(String(10), nullable=False)
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    change_set = relationship("TranscriptChangeSetModel", back_populates="changes")
