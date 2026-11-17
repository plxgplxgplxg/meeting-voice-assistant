import secrets
from typing import Any

from fastapi import APIRouter, Header, Request, status

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.errors import AuthenticationError
from app.schemas.billing import CheckoutRequest, CheckoutResponse, OrderStatusResponse
from app.services.billing.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["VietQR Payments"])


def verify_sepay_api_key(authorization: str | None) -> None:
    """Validate the SePay webhook credential in constant time.

    Args:
        authorization: Raw ``Authorization`` header value, e.g. ``Apikey <key>``.

    Raises:
        AuthenticationError: If a key is configured and the header is missing or wrong.
    """
    expected = settings.sepay_webhook_api_key
    if not expected:
        return

    provided = ""
    if authorization:
        provided = authorization.removeprefix("Apikey ").removeprefix("Bearer ").strip()
    if not provided or not secrets.compare_digest(provided.encode(), expected.encode()):
        raise AuthenticationError("Invalid SePay webhook API key.", code="INVALID_WEBHOOK_KEY")


@router.post("/checkout", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED)
async def create_vietqr_checkout(
    payload: CheckoutRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> CheckoutResponse:
    """Create a new payment order and return VietQR bank transfer instructions."""
    return await PaymentService(db).create_checkout_session(current_user, payload.plan_slug)


@router.get("/orders/{order_code}", response_model=OrderStatusResponse)
async def check_order_status(
    order_code: str, current_user: CurrentUser, db: DbSession
) -> OrderStatusResponse:
    """Check whether one of the caller's payment orders has been paid."""
    return await PaymentService(db).get_order_status(order_code, current_user)


@router.post("/sepay/webhook")
async def handle_sepay_webhook(
    request: Request,
    db: DbSession,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Receive and process incoming bank transfer webhooks from SePay."""
    verify_sepay_api_key(authorization)
    payload = await request.json()
    return await PaymentService(db).process_sepay_webhook(payload)
