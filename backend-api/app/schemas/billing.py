import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class PlanResponse(BaseModel):
    """Schema representing an available subscription plan tier."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    description: str | None = None
    price_amount: float
    currency: str = "VND"
    billing_interval: str
    total_duration_limit_minutes: int
    features: dict[str, Any] = Field(default_factory=dict)
    is_default: bool
    is_active: bool


class SubscriptionResponse(BaseModel):
    """Schema representing user's current subscription and quota usage."""
    id: uuid.UUID
    plan_slug: str
    plan_name: str
    status: str
    current_period_end: datetime
    total_duration_limit_minutes: int
    used_duration_minutes: float
    remaining_duration_minutes: float


class CheckoutRequest(BaseModel):
    """Schema for initiating a plan upgrade / VietQR checkout session."""
    plan_slug: str = Field(min_length=1, max_length=100)


class CheckoutResponse(BaseModel):
    """Schema providing VietQR code URL and bank transfer instructions."""
    order_id: uuid.UUID
    order_code: str
    amount: float
    currency: str = "VND"
    bank_code: str
    account_number: str
    account_name: str
    transfer_content: str
    qr_url: str
    expires_at: datetime
    status: str


class OrderStatusResponse(BaseModel):
    """Schema checking payment order fulfillment status."""
    order_code: str
    status: str
    paid_at: datetime | None = None
