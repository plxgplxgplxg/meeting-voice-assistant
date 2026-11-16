import uuid
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.billing import MeetingQuotaUsageModel, PlanConfigModel, SubscriptionModel
from app.models.user import UserModel
from app.schemas.billing import SubscriptionResponse
from app.services.plan_service import PlanService


class QuotaService:
    """Service tracking audio duration usage and asserting plan quota limits."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.plan_service = PlanService(session)

    async def get_user_subscription_summary(
        self, user: UserModel
    ) -> SubscriptionResponse:
        """Calculate user's current subscription, used minutes, and remaining quota."""
        # Find active subscription
        sub_stmt = (
            select(SubscriptionModel)
            .options(selectinload(SubscriptionModel.plan))
            .where(
                SubscriptionModel.user_id == user.id,
                SubscriptionModel.status == "active",
            )
            .order_by(SubscriptionModel.current_period_end.desc())
        )
        sub = await self.session.scalar(sub_stmt)

        if not sub:
            # Create default free subscription
            free_plan = await self.plan_service.get_plan_by_slug("free")
            if not free_plan:
                await self.plan_service.seed_default_plans_if_empty()
                free_plan = await self.plan_service.get_plan_by_slug("free")

            now = datetime.utcnow()
            sub = SubscriptionModel(
                user_id=user.id,
                plan_config_id=free_plan.id,
                status="active",
                current_period_start=now,
                current_period_end=now + timedelta(days=365 * 10),
                plan_snapshot={"slug": "free", "name": free_plan.name},
            )
            self.session.add(sub)
            await self.session.flush()
            sub.plan = free_plan

        # Calculate used duration in current period
        usage_stmt = select(
            func.coalesce(func.sum(MeetingQuotaUsageModel.duration_seconds), 0.0)
        ).where(
            MeetingQuotaUsageModel.user_id == user.id,
            MeetingQuotaUsageModel.usage_at >= sub.current_period_start,
            MeetingQuotaUsageModel.usage_at <= sub.current_period_end,
        )
        total_used_seconds = float(await self.session.scalar(usage_stmt) or 0.0)
        used_minutes = round(total_used_seconds / 60.0, 1)

        limit_minutes = sub.plan.total_duration_limit_minutes if sub.plan else 60
        if limit_minutes == 0:  # Unlimited
            remaining_minutes = 999999.0
        else:
            remaining_minutes = max(0.0, round(limit_minutes - used_minutes, 1))

        return SubscriptionResponse(
            id=sub.id,
            plan_slug=sub.plan.slug if sub.plan else "free",
            plan_name=sub.plan.name if sub.plan else "Gói Miễn Phí",
            status=sub.status,
            current_period_end=sub.current_period_end,
            total_duration_limit_minutes=limit_minutes,
            used_duration_minutes=used_minutes,
            remaining_duration_minutes=remaining_minutes,
        )

    async def assert_within_quota(self, user: UserModel) -> None:
        """Verify that user has remaining quota before starting/uploading recording.

        Raises:
            HTTPException: If monthly quota has been exhausted.
        """
        summary = await self.get_user_subscription_summary(user)
        if summary.total_duration_limit_minutes > 0 and summary.remaining_duration_minutes <= 0:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Monthly recording quota exhausted ({summary.used_duration_minutes}/{summary.total_duration_limit_minutes} minutes). Please upgrade your plan.",
            )

    async def record_usage(
        self, user_id: uuid.UUID, meeting_id: uuid.UUID | None, duration_seconds: float
    ) -> None:
        """Record audio duration consumed by a meeting."""
        if duration_seconds <= 0:
            return

        usage = MeetingQuotaUsageModel(
            user_id=user_id,
            meeting_id=meeting_id,
            duration_seconds=duration_seconds,
            usage_at=datetime.utcnow(),
        )
        self.session.add(usage)
        await self.session.flush()
