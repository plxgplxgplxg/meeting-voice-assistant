import re
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.billing import (
    PaymentOrderModel,
    PlanConfigModel,
    SepayWebhookEventModel,
    SubscriptionModel,
)
from app.models.user import UserModel
from app.schemas.billing import CheckoutResponse, OrderStatusResponse
from app.services.plan_service import PlanService


class PaymentService:
    """Service handling VietQR checkout session generation and SePay webhook processing."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.plan_service = PlanService(session)

    async def create_checkout_session(
        self, user: UserModel, plan_slug: str
    ) -> CheckoutResponse:
        """Create a payment order and generate dynamic VietQR transfer instructions.

        Args:
            user: Authenticated user purchasing the plan.
            plan_slug: Target plan tier slug (e.g. 'pro', 'unlimited').

        Returns:
            CheckoutResponse with VietQR image URL and transfer details.

        Raises:
            HTTPException: If plan not found or already free.
        """
        plan = await self.plan_service.get_plan_by_slug(plan_slug)
        if not plan or plan.price_amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid plan for checkout '{plan_slug}'.",
            )

        # Generate unique order code (e.g. MVA192837)
        order_code = f"MVA{secrets.randbelow(900000) + 100000}"
        expires_at = datetime.utcnow() + timedelta(minutes=30)
        amount_int = int(plan.price_amount)

        # Build SePay VietQR Image URL
        # Format: https://qr.sepay.vn/img?bank={bank}&acc={acc}&template=compact&amount={amount}&des={des}
        qr_url = (
            f"https://qr.sepay.vn/img?"
            f"bank={quote(settings.sepay_bank_code)}&"
            f"acc={quote(settings.sepay_account_number)}&"
            f"template=compact&"
            f"amount={amount_int}&"
            f"des={quote(order_code)}"
        )

        order = PaymentOrderModel(
            order_code=order_code,
            user_id=user.id,
            plan_config_id=plan.id,
            amount=float(amount_int),
            currency=plan.currency,
            payment_method="sepay",
            status="pending",
            qr_url=qr_url,
            description=f"Thanh toan {plan.name} - {order_code}",
            expires_at=expires_at,
        )
        self.session.add(order)
        await self.session.flush()

        return CheckoutResponse(
            order_id=order.id,
            order_code=order.order_code,
            amount=order.amount,
            currency=order.currency,
            bank_code=settings.sepay_bank_code,
            account_number=settings.sepay_account_number,
            account_name=settings.sepay_account_name,
            transfer_content=order_code,
            qr_url=qr_url,
            expires_at=expires_at,
            status=order.status,
        )

    async def get_order_status(self, order_code: str) -> OrderStatusResponse:
        """Query status of a payment order."""
        order = await self.session.scalar(
            select(PaymentOrderModel).where(PaymentOrderModel.order_code == order_code)
        )
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found."
            )

        return OrderStatusResponse(
            order_code=order.order_code,
            status=order.status,
            paid_at=order.paid_at,
        )

    async def process_sepay_webhook(self, payload: dict[str, Any]) -> dict[str, str]:
        """Process incoming transfer event webhook from SePay.

        Args:
            payload: Webhook payload containing transaction details.

        Returns:
            Dictionary with processing result status.
        """
        transaction_id = str(payload.get("id") or payload.get("transactionId") or uuid.uuid4())

        # Check for duplicate webhook event (idempotency)
        existing_event = await self.session.scalar(
            select(SepayWebhookEventModel).where(
                SepayWebhookEventModel.sepay_transaction_id == transaction_id
            )
        )
        if existing_event:
            return {"status": "duplicate", "message": "Transaction already processed."}

        # Extract transfer amount and content text
        transfer_amount = float(payload.get("transferAmount") or payload.get("amount") or 0.0)
        content_text = str(payload.get("content") or payload.get("code") or "")

        # Match order code (e.g. MVA123456)
        match = re.search(r"MVA\d{6}", content_text.upper())
        matched_order_code = match.group(0) if match else None

        order = None
        if matched_order_code:
            order = await self.session.scalar(
                select(PaymentOrderModel).where(
                    PaymentOrderModel.order_code == matched_order_code
                )
            )

        webhook_event = SepayWebhookEventModel(
            sepay_transaction_id=transaction_id,
            payment_order_id=order.id if order else None,
            code=matched_order_code,
            reference_code=str(payload.get("referenceCode") or ""),
            transfer_amount=transfer_amount,
            account_number=str(payload.get("accountNumber") or ""),
            raw_payload=payload,
            processing_status="pending",
        )
        self.session.add(webhook_event)

        if not order:
            webhook_event.processing_status = "ignored"
            await self.session.flush()
            return {"status": "ignored", "reason": "No matching order code found in transfer content."}

        if order.status == "completed":
            webhook_event.processing_status = "duplicate"
            await self.session.flush()
            return {"status": "duplicate", "message": "Order already marked as completed."}

        if transfer_amount < order.amount:
            webhook_event.processing_status = "partial_amount"
            await self.session.flush()
            return {"status": "partial_amount", "reason": "Transfer amount is lower than required order amount."}

        # Mark order as completed
        now = datetime.utcnow()
        order.status = "completed"
        order.paid_at = now
        self.session.add(order)

        # Activate or extend user's subscription
        plan = await self.session.get(PlanConfigModel, order.plan_config_id)
        if plan:
            active_sub = await self.session.scalar(
                select(SubscriptionModel).where(
                    SubscriptionModel.user_id == order.user_id,
                    SubscriptionModel.status == "active",
                )
            )

            start_date = max(now, active_sub.current_period_end) if active_sub else now
            end_date = start_date + timedelta(days=30)

            if active_sub:
                active_sub.plan_config_id = plan.id
                active_sub.current_period_start = start_date
                active_sub.current_period_end = end_date
                active_sub.plan_snapshot = {
                    "slug": plan.slug,
                    "name": plan.name,
                    "duration_limit": plan.total_duration_limit_minutes,
                }
                self.session.add(active_sub)
            else:
                new_sub = SubscriptionModel(
                    user_id=order.user_id,
                    plan_config_id=plan.id,
                    status="active",
                    current_period_start=start_date,
                    current_period_end=end_date,
                    plan_snapshot={
                        "slug": plan.slug,
                        "name": plan.name,
                        "duration_limit": plan.total_duration_limit_minutes,
                    },
                )
                self.session.add(new_sub)

        webhook_event.processing_status = "processed"
        await self.session.flush()

        return {"status": "success", "order_code": order.order_code, "plan": plan.name if plan else "Unknown"}
