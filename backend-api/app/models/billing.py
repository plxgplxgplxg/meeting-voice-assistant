import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utc_now
from app.core.database import Base
from app.domain.enums import OrderStatus, SubscriptionStatus, WebhookEventStatus
from app.models.constraints import enum_check
from app.models.types import UTCDateTime


class PlanConfigModel(Base):
    """Database model representing a subscription tier configuration."""
    __tablename__ = "plan_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(10), default="VND", nullable=False)
    billing_interval: Mapped[str] = mapped_column(
        String(50), default="monthly", nullable=False
    )  # monthly, yearly, one_time
    total_duration_limit_minutes: Mapped[int] = mapped_column(
        Integer, default=60, nullable=False
    )  # 60 min for Free, 600 min for Pro, 0 = unlimited
    features: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, server_default=func.now(), nullable=False
    )


class SubscriptionModel(Base):
    """Database model representing an active user subscription."""
    __tablename__ = "subscriptions"
    __table_args__ = (enum_check("status", SubscriptionStatus, "status"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    plan_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plan_configs.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), default="active", nullable=False
    )  # active, expired, replaced, cancelled
    current_period_start: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, server_default=func.now(), nullable=False
    )
    current_period_end: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    plan_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, server_default=func.now(), nullable=False
    )

    user = relationship("UserModel", back_populates="subscriptions")
    plan = relationship("PlanConfigModel")


class MeetingQuotaUsageModel(Base):
    """Database model tracking audio duration quota consumption."""
    __tablename__ = "meeting_quota_usage_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    meeting_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="SET NULL"), nullable=True
    )
    audio_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audio_files.id", ondelete="SET NULL"),
        unique=True,
        nullable=True,
    )
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    usage_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, server_default=func.now(), nullable=False
    )


class PaymentOrderModel(Base):
    """Database model representing a payment transaction order."""
    __tablename__ = "payment_orders"
    __table_args__ = (enum_check("status", OrderStatus, "status"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_code: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    plan_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plan_configs.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="VND", nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50), default="sepay", nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending, completed, expired, failed
    qr_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, server_default=func.now(), nullable=False
    )

    user = relationship("UserModel", back_populates="payment_orders")
    plan = relationship("PlanConfigModel")


class SepayWebhookEventModel(Base):
    """Database model storing incoming SePay payment webhook records."""
    __tablename__ = "sepay_webhook_events"
    __table_args__ = (enum_check("processing_status", WebhookEventStatus, "processing_status"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sepay_transaction_id: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    payment_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payment_orders.id", ondelete="SET NULL"), nullable=True
    )
    code: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    reference_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transfer_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    account_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    processing_status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending, processed, ignored
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, server_default=func.now(), nullable=False
    )
