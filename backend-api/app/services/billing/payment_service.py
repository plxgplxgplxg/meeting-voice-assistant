import re
import secrets
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utc_now
from app.core.config import settings
from app.core.errors import ConflictError, NotFoundError, ValidationFailedError
from app.domain.enums import OrderStatus, WebhookEventStatus
from app.models.billing import PaymentOrderModel, PlanConfigModel, SepayWebhookEventModel
from app.models.user import UserModel
from app.schemas.billing import CheckoutResponse, OrderStatusResponse
from app.services.billing.plan_service import PlanService
from app.services.billing.subscription_service import SubscriptionService

ORDER_CODE_PATTERN = re.compile(r"MVA[0-9A-F]{10}")
ORDER_TTL = timedelta(minutes=30)
ORDER_CODE_ATTEMPTS = 5


def parse_money(raw: Any) -> Decimal:
    """Parse a webhook amount into a non-negative Decimal.

    Args:
        raw: Numeric or string amount from the webhook payload.

    Returns:
        Decimal amount, zero when the value is missing or malformed.
    """
    try:
        value = Decimal(str(raw if raw is not None else 0))
    except InvalidOperation:
        return Decimal(0)
    return value if value >= 0 else Decimal(0)


class PaymentService:
    """Service handling VietQR checkout session generation and SePay webhook processing."""

    def __init__(
        self,
        session: AsyncSession,
        plan_service: PlanService | None = None,
        subscription_service: SubscriptionService | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            session: Active SQLAlchemy session.
            plan_service: Plan lookup collaborator.
            subscription_service: Collaborator that activates paid plans.
        """
        self.session = session
        self.plan_service = plan_service or PlanService(session)
        self.subscription_service = subscription_service or SubscriptionService(session)

    async def create_checkout_session(self, user: UserModel, plan_slug: str) -> CheckoutResponse:
        """Create a payment order and generate dynamic VietQR transfer instructions.

        Args:
            user: Authenticated user purchasing the plan.
            plan_slug: Target plan tier slug (e.g. 'pro', 'business').

        Returns:
            CheckoutResponse with VietQR image URL and transfer details.

        Raises:
            ValidationFailedError: If the plan does not exist or is free.
            ConflictError: If a unique order code could not be generated.
        """
        plan = await self.plan_service.get_plan_by_slug(plan_slug)
        if not plan or plan.price_amount <= 0:
            raise ValidationFailedError(
                f"Invalid plan for checkout '{plan_slug}'.", code="INVALID_PLAN"
            )

        order_code = await self._generate_order_code()
        expires_at = utc_now() + ORDER_TTL
        amount = plan.price_amount.quantize(Decimal("1"))

        qr_url = (
            f"https://qr.sepay.vn/img?"
            f"bank={quote(settings.sepay_bank_code)}&"
            f"acc={quote(settings.sepay_account_number)}&"
            f"template=compact&"
            f"amount={int(amount)}&"
            f"des={quote(order_code)}"
        )

        order = PaymentOrderModel(
            order_code=order_code,
            user_id=user.id,
            plan_config_id=plan.id,
            amount=amount,
            currency=plan.currency,
            payment_method="sepay",
            status=OrderStatus.PENDING,
            qr_url=qr_url,
            description=f"Thanh toan {plan.name} - {order_code}",
            expires_at=expires_at,
        )
        self.session.add(order)
        await self.session.flush()

        return CheckoutResponse(
            order_id=order.id,
            order_code=order.order_code,
            amount=float(order.amount),
            currency=order.currency,
            bank_code=settings.sepay_bank_code,
            account_number=settings.sepay_account_number,
            account_name=settings.sepay_account_name,
            transfer_content=order_code,
            qr_url=qr_url,
            expires_at=expires_at,
            status=order.status,
        )

    async def get_order_status(self, order_code: str, user: UserModel) -> OrderStatusResponse:
        """Query the status of one of the caller's payment orders.

        Args:
            order_code: Public order code.
            user: Authenticated caller; must own the order.

        Returns:
            Order status summary.

        Raises:
            NotFoundError: If the order does not exist or belongs to someone else.
        """
        order = await self.session.scalar(
            select(PaymentOrderModel).where(
                PaymentOrderModel.order_code == order_code,
                PaymentOrderModel.user_id == user.id,
            )
        )
        if not order:
            raise NotFoundError("Order not found.", code="ORDER_NOT_FOUND")

        return OrderStatusResponse(
            order_code=order.order_code, status=order.status, paid_at=order.paid_at
        )

    async def process_sepay_webhook(self, payload: dict[str, Any]) -> dict[str, str]:
        """Process an incoming transfer event webhook from SePay.

        The event row is inserted first and its unique transaction id acts as
        the idempotency gate. The matching order is then locked so concurrent
        deliveries for one order activate the plan at most once.

        Args:
            payload: Webhook payload containing transaction details.

        Returns:
            Dictionary describing the processing outcome.

        Raises:
            ValidationFailedError: If the payload carries no transaction id.
        """
        raw_id = payload.get("id") or payload.get("transactionId")
        if raw_id is None or str(raw_id).strip() == "":
            raise ValidationFailedError(
                "Webhook payload is missing a transaction id.",
                code="INVALID_WEBHOOK_PAYLOAD",
                status_code=400,
            )
        transaction_id = str(raw_id)

        transfer_amount = parse_money(payload.get("transferAmount") or payload.get("amount"))
        content_text = str(payload.get("content") or payload.get("code") or "")
        match = ORDER_CODE_PATTERN.search(content_text.upper())
        matched_code = match.group(0) if match else None

        event = SepayWebhookEventModel(
            sepay_transaction_id=transaction_id,
            code=matched_code,
            reference_code=str(payload.get("referenceCode") or ""),
            transfer_amount=transfer_amount,
            account_number=str(payload.get("accountNumber") or ""),
            raw_payload=payload,
            processing_status=WebhookEventStatus.PENDING,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(event)
                await self.session.flush()
        except IntegrityError:
            return {"status": "duplicate", "message": "Transaction already processed."}

        order = None
        if matched_code:
            order = await self.session.scalar(
                select(PaymentOrderModel)
                .where(PaymentOrderModel.order_code == matched_code)
                .with_for_update()
            )

        if not order:
            event.processing_status = WebhookEventStatus.IGNORED
            await self.session.flush()
            return {
                "status": "ignored",
                "reason": "No matching order code found in transfer content.",
            }
        event.payment_order_id = order.id

        if order.status == OrderStatus.COMPLETED:
            event.processing_status = WebhookEventStatus.DUPLICATE
            await self.session.flush()
            return {"status": "duplicate", "message": "Order already marked as completed."}

        now = utc_now()
        if order.expires_at < now:
            if order.status == OrderStatus.PENDING:
                order.status = OrderStatus.EXPIRED
            event.processing_status = WebhookEventStatus.EXPIRED_ORDER
            await self.session.flush()
            return {"status": "expired_order", "reason": "Order expired before payment arrived."}

        if transfer_amount < order.amount:
            event.processing_status = WebhookEventStatus.PARTIAL_AMOUNT
            await self.session.flush()
            return {
                "status": "partial_amount",
                "reason": "Transfer amount is lower than required order amount.",
            }

        order.status = OrderStatus.COMPLETED
        order.paid_at = now
        plan = await self.session.get(PlanConfigModel, order.plan_config_id)
        if plan:
            await self.subscription_service.activate_paid_plan(order.user_id, plan, now)

        event.processing_status = WebhookEventStatus.PROCESSED
        await self.session.flush()
        return {
            "status": "success",
            "order_code": order.order_code,
            "plan": plan.name if plan else "Unknown",
        }

    async def _generate_order_code(self) -> str:
        """Generate an unguessable, unique order code.

        Returns:
            Order code of the form ``MVA`` followed by 10 uppercase hex characters.

        Raises:
            ConflictError: If every attempt collided with an existing code.
        """
        for _ in range(ORDER_CODE_ATTEMPTS):
            candidate = f"MVA{secrets.token_hex(5).upper()}"
            taken = await self.session.scalar(
                select(PaymentOrderModel.id).where(PaymentOrderModel.order_code == candidate)
            )
            if not taken:
                return candidate
        raise ConflictError("Could not allocate an order code, please retry.", code="ORDER_CODE_COLLISION")
