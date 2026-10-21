import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MeetingModel(Base):
    """Database model representing a meeting session."""
    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="created", nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    segments = relationship(
        "TranscriptSegmentModel", back_populates="meeting", cascade="all, delete-orphan"
    )
    summary = relationship(
        "SummaryModel", back_populates="meeting", uselist=False, cascade="all, delete-orphan"
    )
