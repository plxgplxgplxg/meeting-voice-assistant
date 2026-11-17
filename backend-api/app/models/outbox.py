import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utc_now
from app.core.database import Base
from app.models.types import UTCDateTime


class OutboxEventModel(Base):
    """Task to publish to the broker, written in the same transaction as the change that needs it.

    A relay polls undispatched rows, so a Redis outage or a crash between commit
    and publish never loses work.
    """
    __tablename__ = "outbox_events"
    __table_args__ = (
        Index(
            "ix_outbox_events_pending",
            "created_at",
            postgresql_where="dispatched_at IS NULL",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    task_name: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, server_default=func.now(), nullable=False
    )
    available_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
