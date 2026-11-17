import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utc_now
from app.core.database import Base
from app.models.types import UTCDateTime


class AudioFileModel(Base):
    """Database model representing an uploaded or recorded audio/video file."""
    __tablename__ = "audio_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), default="audio/wav", nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    upload_status: Mapped[str] = mapped_column(
        String(50), default="completed", nullable=False
    )  # pending, completed, failed
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, server_default=func.now(), nullable=False
    )

    meeting = relationship("MeetingModel", back_populates="audio_files")
