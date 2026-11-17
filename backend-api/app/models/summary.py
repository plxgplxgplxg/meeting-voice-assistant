import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utc_now
from app.core.database import Base
from app.models.constraints import enum_check
from app.models.types import UTCDateTime


class SummaryModel(Base):
    """Database model representing an AI generated meeting summary."""
    __tablename__ = "meeting_summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_points: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, server_default=func.now(), nullable=False
    )

    meeting = relationship("MeetingModel", back_populates="summary")


class ActionItemModel(Base):
    """Database model representing an assigned action item from a meeting."""
    __tablename__ = "action_items"
    __table_args__ = (
        enum_check("status", ("pending", "completed"), "status"),
        enum_check("source", ("ai", "user"), "source"),
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
    description: Mapped[str] = mapped_column(Text, nullable=False)
    assignee: Mapped[str] = mapped_column(String(150), default="Unassigned", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    source: Mapped[str] = mapped_column(String(10), default="user", nullable=False)  # ai, user
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, server_default=func.now(), nullable=False
    )
