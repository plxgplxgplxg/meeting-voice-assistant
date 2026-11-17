import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utc_now
from app.core.database import Base
from app.models.types import UTCDateTime


class TranscriptSegmentModel(Base):
    """Database model representing an individual spoken turn in a meeting."""
    __tablename__ = "transcript_segments"
    __table_args__ = (UniqueConstraint("meeting_id", "sequence_order"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    speaker_label: Mapped[str] = mapped_column(String(100), default="Speaker 1", nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, server_default=func.now(), nullable=False
    )

    meeting = relationship("MeetingModel", back_populates="segments")
