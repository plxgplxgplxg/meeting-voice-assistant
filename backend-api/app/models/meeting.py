import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
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
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    share_token: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    share_permission: Mapped[str] = mapped_column(
        String(20), default="viewer", nullable=False
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    creator = relationship("UserModel")
    audio_files = relationship(
        "AudioFileModel", back_populates="meeting", cascade="all, delete-orphan"
    )
    segments = relationship(
        "TranscriptSegmentModel", back_populates="meeting", cascade="all, delete-orphan"
    )
    summary = relationship(
        "SummaryModel", back_populates="meeting", uselist=False, cascade="all, delete-orphan"
    )
    project_links = relationship(
        "ProjectMeetingModel", back_populates="meeting", cascade="all, delete-orphan"
    )
