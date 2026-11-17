from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.billing import PlanResponse, SubscriptionResponse
from app.services.billing.plan_service import PlanService
from app.services.billing.quota_service import QuotaService

router = APIRouter(prefix="/plans", tags=["Plans & Subscriptions"])



@router.get("", response_model=list[PlanResponse])
async def list_available_plans(db: DbSession) -> list[PlanResponse]:
    """Retrieve all available subscription plans."""
    service = PlanService(db)
    plans = await service.list_active_plans()
    return [PlanResponse.model_validate(p) for p in plans]


@router.get("/my-subscription", response_model=SubscriptionResponse)
async def get_my_subscription(
    current_user: CurrentUser, db: DbSession
) -> SubscriptionResponse:
    """Retrieve current subscription plan and audio duration quota usage."""
    quota_service = QuotaService(db)
    return await quota_service.get_user_subscription_summary(current_user)
