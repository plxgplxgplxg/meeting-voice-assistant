from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.models.user import UserModel
from app.schemas.billing import PlanResponse, SubscriptionResponse
from app.services.plan_service import PlanService
from app.services.quota_service import QuotaService

router = APIRouter(prefix="/plans", tags=["Plans & Subscriptions"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
CurrentUser = Annotated[UserModel, Depends(get_current_user)]


@router.get("", response_model=list[PlanResponse])
async def list_available_plans(db: DatabaseSession) -> list[PlanResponse]:
    """Retrieve all available subscription plans."""
    service = PlanService(db)
    plans = await service.list_active_plans()
    return [PlanResponse.model_validate(p) for p in plans]


@router.get("/my-subscription", response_model=SubscriptionResponse)
async def get_my_subscription(
    current_user: CurrentUser, db: DatabaseSession
) -> SubscriptionResponse:
    """Retrieve current subscription plan and audio duration quota usage."""
    quota_service = QuotaService(db)
    return await quota_service.get_user_subscription_summary(current_user)
