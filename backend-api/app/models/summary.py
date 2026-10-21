import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


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
    key_points: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    meeting = relationship("MeetingModel", back_populates="summary")


class ActionItemModel(Base):
    """Database model representing an assigned action item from a meeting."""
    __tablename__ = "action_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    assignee: Mapped[str] = mapped_column(String(150), default="Unassigned", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
