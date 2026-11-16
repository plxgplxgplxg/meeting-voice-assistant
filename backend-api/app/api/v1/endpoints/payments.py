from typing import Annotated, Any
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.security import get_current_user
from app.models.user import UserModel
from app.schemas.billing import CheckoutRequest, CheckoutResponse, OrderStatusResponse
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["VietQR Payments"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
CurrentUser = Annotated[UserModel, Depends(get_current_user)]


@router.post("/checkout", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED)
async def create_vietqr_checkout(
    payload: CheckoutRequest,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> CheckoutResponse:
    """Create a new payment order and return VietQR bank transfer instructions."""
    service = PaymentService(db)
    return await service.create_checkout_session(current_user, payload.plan_slug)


@router.get("/orders/{order_code}", response_model=OrderStatusResponse)
async def check_order_status(
    order_code: str, db: DatabaseSession
) -> OrderStatusResponse:
    """Check whether a payment order has been paid and completed."""
    service = PaymentService(db)
    return await service.get_order_status(order_code)


@router.post("/sepay/webhook")
async def handle_sepay_webhook(
    request: Request,
    db: DatabaseSession,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Receive and process incoming bank transfer webhooks from SePay."""
    # Optional authorization key check if configured
    if settings.sepay_webhook_api_key and authorization:
        token = authorization.replace("Apikey ", "").replace("Bearer ", "").strip()
        if token != settings.sepay_webhook_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid SePay webhook API key.",
            )

    payload = await request.json()
    service = PaymentService(db)
    return await service.process_sepay_webhook(payload)
