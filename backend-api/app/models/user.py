import uuid
from datetime import datetime

from sqlalchemy import Boolean, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utc_now
from app.core.database import Base
from app.models.types import UTCDateTime


class UserModel(Base):
    """Database model representing a registered user."""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
        nullable=False,
    )

    projects_owned = relationship(
        "ProjectModel", back_populates="owner", cascade="all, delete-orphan"
    )
    project_memberships = relationship(
        "ProjectMemberModel", back_populates="user", cascade="all, delete-orphan"
    )
    subscriptions = relationship(
        "SubscriptionModel", back_populates="user", cascade="all, delete-orphan"
    )
    payment_orders = relationship(
        "PaymentOrderModel", back_populates="user", cascade="all, delete-orphan"
    )
