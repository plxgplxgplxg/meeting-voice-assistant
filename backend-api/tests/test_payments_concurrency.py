import asyncio
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.clock import utc_now
from app.models.billing import PaymentOrderModel, PlanConfigModel, SubscriptionModel
from app.models.user import UserModel
from app.services.billing.payment_service import PaymentService
from app.services.billing.plan_service import PlanService
from tests.conftest import TEST_DATABASE_URL

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="row locking requires PostgreSQL (set TEST_DATABASE_URL)"
)


@pytest.mark.asyncio
async def test_concurrent_webhooks_for_one_order_activate_the_plan_once(
    test_engine: AsyncEngine,
) -> None:
    """Two simultaneous deliveries serialize on the order row and activate a single subscription."""
    factory = async_sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)

    async with factory() as setup:
        await PlanService(setup).seed_default_plans()
        user = UserModel(email="race@example.com", full_name="Race", password_hash="x")
        setup.add(user)
        await setup.flush()
        pro = await setup.scalar(select(PlanConfigModel).where(PlanConfigModel.slug == "pro"))
        setup.add(
            PaymentOrderModel(
                order_code="MVA0000000001",
                user_id=user.id,
                plan_config_id=pro.id,
                amount=Decimal("99000"),
                expires_at=utc_now().replace(year=utc_now().year + 1),
            )
        )
        await setup.commit()
        user_id = user.id

    async def deliver(transaction_id: str) -> dict[str, str]:
        async with factory() as session:
            result = await PaymentService(session).process_sepay_webhook(
                {"id": transaction_id, "transferAmount": 99000, "content": "MVA0000000001"}
            )
            await session.commit()
            return result

    outcomes = await asyncio.gather(deliver("T1"), deliver("T2"))
    assert sorted(o["status"] for o in outcomes) == ["duplicate", "success"]

    async with factory() as check:
        paid = await check.scalar(
            select(func.count())
            .select_from(SubscriptionModel)
            .join(PlanConfigModel, PlanConfigModel.id == SubscriptionModel.plan_config_id)
            .where(SubscriptionModel.user_id == user_id, PlanConfigModel.slug == "pro")
        )
    assert paid == 1


@pytest.mark.asyncio
async def test_same_transaction_id_delivered_twice_at_once_is_deduplicated(
    test_engine: AsyncEngine,
) -> None:
    """The unique transaction id gate turns a racing duplicate into a clean no-op, not a 500."""
    factory = async_sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    async with factory() as setup:
        await PlanService(setup).seed_default_plans()
        await setup.commit()

    async def deliver() -> dict[str, str]:
        async with factory() as session:
            result = await PaymentService(session).process_sepay_webhook(
                {"id": "SAME", "transferAmount": 1, "content": "no order here"}
            )
            await session.commit()
            return result

    outcomes = await asyncio.gather(deliver(), deliver())
    assert sorted(o["status"] for o in outcomes) == ["duplicate", "ignored"]
