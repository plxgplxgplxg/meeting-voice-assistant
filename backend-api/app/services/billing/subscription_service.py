import uuid
from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.clock import utc_now
from app.core.errors import DomainError
from app.domain.enums import SubscriptionStatus
from app.models.billing import PlanConfigModel, SubscriptionModel
from app.services.billing.plan_service import is_free_plan

BILLING_PERIOD = timedelta(days=30)


def build_plan_snapshot(plan: PlanConfigModel) -> dict[str, object]:
    """Capture plan attributes that must survive later plan edits.

    Args:
        plan: Plan the subscription was created for.

    Returns:
        JSON-serializable snapshot stored on the subscription row.
    """
    return {
        "slug": plan.slug,
        "name": plan.name,
        "duration_limit": plan.total_duration_limit_minutes,
    }


class SubscriptionService:
    """Service owning subscription periods, the Free monthly rollover, and plan activation."""

    def __init__(
        self,
        session: AsyncSession,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        """Initialize the service.

        Args:
            session: Active SQLAlchemy session.
            clock: Source of the current time, injectable for tests.
        """
        self.session = session
        self.clock = clock

    async def get_current(self, user_id: uuid.UUID) -> SubscriptionModel:
        """Return the subscription that governs the user right now.

        A paid subscription wins while its period contains now. Otherwise the
        Free subscription applies and its monthly window is rolled forward
        lazily. Expired paid rows are closed and a Free row is created when
        none exists.

        Args:
            user_id: Owner of the subscription.

        Returns:
            Active subscription with its plan loaded.

        Raises:
            DomainError: If the Free plan has not been seeded.
        """
        now = self.clock()
        rows = (
            await self.session.scalars(
                select(SubscriptionModel)
                .options(selectinload(SubscriptionModel.plan))
                .where(
                    SubscriptionModel.user_id == user_id,
                    SubscriptionModel.status == SubscriptionStatus.ACTIVE,
                )
                .order_by(SubscriptionModel.current_period_start.desc())
            )
        ).all()

        paid_current: SubscriptionModel | None = None
        free_sub: SubscriptionModel | None = None
        for sub in rows:
            if is_free_plan(sub.plan):
                free_sub = free_sub or sub
            elif sub.current_period_start <= now < sub.current_period_end:
                paid_current = paid_current or sub
            elif sub.current_period_end <= now:
                sub.status = SubscriptionStatus.EXPIRED

        if paid_current:
            return paid_current
        if free_sub:
            self._roll_free_period(free_sub, now)
            return free_sub
        return await self.create_free_subscription(user_id, now)

    async def create_free_subscription(
        self, user_id: uuid.UUID, now: datetime | None = None
    ) -> SubscriptionModel:
        """Create a Free subscription anchored at ``now``.

        Args:
            user_id: Owner of the new subscription.
            now: Anchor time, defaults to the service clock.

        Returns:
            Newly persisted subscription with its plan loaded.

        Raises:
            DomainError: If the Free plan has not been seeded.
        """
        now = now or self.clock()
        free_plan = await self.session.scalar(
            select(PlanConfigModel).where(
                PlanConfigModel.price_amount <= 0, PlanConfigModel.is_active.is_(True)
            )
        )
        if not free_plan:
            raise DomainError(
                "Free plan is not configured.", code="PLAN_NOT_CONFIGURED", status_code=503
            )

        sub = SubscriptionModel(
            user_id=user_id,
            plan_config_id=free_plan.id,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=now,
            current_period_end=now + BILLING_PERIOD,
            plan_snapshot=build_plan_snapshot(free_plan),
        )
        self.session.add(sub)
        await self.session.flush()
        sub.plan = free_plan
        return sub

    async def activate_paid_plan(
        self, user_id: uuid.UUID, plan: PlanConfigModel, paid_at: datetime
    ) -> SubscriptionModel:
        """Activate or extend a paid plan after a confirmed payment.

        - From Free or from a different paid plan the new period starts at
          ``paid_at`` and every open subscription is closed as ``replaced``.
        - For the same paid plan the new period starts when the latest
          existing period of that plan ends.

        A new row is always inserted so subscription history is preserved.

        Args:
            user_id: Subscriber.
            plan: Plan that was paid for.
            paid_at: Time the payment was confirmed.

        Returns:
            The newly created subscription row.
        """
        current = await self.get_current(user_id)

        if not is_free_plan(current.plan) and current.plan_config_id == plan.id:
            latest_end = await self.session.scalar(
                select(func.max(SubscriptionModel.current_period_end)).where(
                    SubscriptionModel.user_id == user_id,
                    SubscriptionModel.plan_config_id == plan.id,
                    SubscriptionModel.status == SubscriptionStatus.ACTIVE,
                )
            )
            start = max(paid_at, latest_end or paid_at)
        else:
            start = paid_at
            open_rows = await self.session.scalars(
                select(SubscriptionModel).where(
                    SubscriptionModel.user_id == user_id,
                    SubscriptionModel.status == SubscriptionStatus.ACTIVE,
                )
            )
            for row in open_rows:
                row.status = SubscriptionStatus.REPLACED

        new_sub = SubscriptionModel(
            user_id=user_id,
            plan_config_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=start,
            current_period_end=start + BILLING_PERIOD,
            plan_snapshot=build_plan_snapshot(plan),
        )
        self.session.add(new_sub)
        await self.session.flush()
        new_sub.plan = plan
        return new_sub

    @staticmethod
    def _roll_free_period(sub: SubscriptionModel, now: datetime) -> None:
        """Advance a Free subscription to the monthly window containing ``now``."""
        if now < sub.current_period_end:
            return
        elapsed_periods = (now - sub.current_period_start) // BILLING_PERIOD
        sub.current_period_start = sub.current_period_start + elapsed_periods * BILLING_PERIOD
        sub.current_period_end = sub.current_period_start + BILLING_PERIOD
