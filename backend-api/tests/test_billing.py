from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utc_now
from app.core.errors import QuotaExceededError
from app.models.audio_file import AudioFileModel
from app.models.billing import PlanConfigModel, SubscriptionModel
from app.models.meeting import MeetingModel
from app.models.user import UserModel
from app.services.billing.plan_service import PlanService
from app.services.billing.quota_service import QuotaService
from app.services.billing.subscription_service import BILLING_PERIOD, SubscriptionService


async def make_user(db: AsyncSession, email: str = "u@example.com") -> UserModel:
    user = UserModel(email=email, full_name="User", password_hash="x")
    db.add(user)
    await db.flush()
    return user


async def plan(db: AsyncSession, slug: str) -> PlanConfigModel:
    return await db.scalar(select(PlanConfigModel).where(PlanConfigModel.slug == slug))


@pytest.mark.asyncio
async def test_free_usage_resets_after_thirty_days(db_session: AsyncSession) -> None:
    """The Free quota is monthly and rolls forward lazily from the signup anchor."""
    user = await make_user(db_session)
    signup = utc_now()
    subs = SubscriptionService(db_session, clock=lambda: signup)
    await subs.create_free_subscription(user.id, signup)

    quota = QuotaService(db_session, SubscriptionService(db_session, clock=lambda: signup))
    await quota.record_usage(user.id, None, 60 * 60)
    summary = await quota.get_user_subscription_summary(user)
    assert summary.remaining_duration_minutes == 0.0

    later = signup + BILLING_PERIOD + timedelta(hours=1)
    quota_later = QuotaService(db_session, SubscriptionService(db_session, clock=lambda: later))
    summary_later = await quota_later.get_user_subscription_summary(user)
    assert summary_later.used_duration_minutes == 0.0
    assert summary_later.remaining_duration_minutes == 60.0
    assert summary_later.current_period_end > later


@pytest.mark.asyncio
async def test_upload_blocked_when_quota_is_exhausted(db_session: AsyncSession) -> None:
    """assert_within_quota raises 402 once remaining minutes reach zero."""
    user = await make_user(db_session)
    quota = QuotaService(db_session)
    await quota.subscriptions.create_free_subscription(user.id)
    await quota.assert_within_quota(user)

    await quota.record_usage(user.id, None, 61 * 60)
    with pytest.raises(QuotaExceededError) as exc:
        await quota.assert_within_quota(user)
    assert exc.value.status_code == 402


@pytest.mark.asyncio
async def test_usage_is_recorded_once_per_audio_file(db_session: AsyncSession) -> None:
    """Reprocessing the same audio never charges twice."""
    user = await make_user(db_session)
    quota = QuotaService(db_session)
    await quota.subscriptions.create_free_subscription(user.id)
    meeting = MeetingModel(title="m", status="ready", created_by=user.id)
    db_session.add(meeting)
    await db_session.flush()
    audio = AudioFileModel(meeting_id=meeting.id, file_name="a.wav", storage_key="k/a.wav")
    db_session.add(audio)
    await db_session.flush()
    audio_id = audio.id

    assert await quota.record_usage(user.id, None, 120, audio_file_id=None) is True
    assert await quota.record_usage(user.id, None, 300, audio_file_id=audio_id) is True
    assert await quota.record_usage(user.id, None, 300, audio_file_id=audio_id) is False
    assert await quota.record_usage(user.id, None, 0) is False


@pytest.mark.asyncio
async def test_free_to_paid_upgrade_starts_now_and_replaces_free(db_session: AsyncSession) -> None:
    """Activating Pro from Free starts today and closes the Free row."""
    user = await make_user(db_session)
    now = utc_now()
    subs = SubscriptionService(db_session, clock=lambda: now)
    free = await subs.create_free_subscription(user.id, now)

    pro_sub = await subs.activate_paid_plan(user.id, await plan(db_session, "pro"), now)
    assert pro_sub.current_period_start == now
    assert pro_sub.current_period_end == now + BILLING_PERIOD
    assert free.status == "replaced"
    assert (await subs.get_current(user.id)).id == pro_sub.id


@pytest.mark.asyncio
async def test_same_plan_renewal_is_appended_after_current_period(db_session: AsyncSession) -> None:
    """Renewing the same paid plan queues the next period after the latest one."""
    user = await make_user(db_session)
    now = utc_now()
    subs = SubscriptionService(db_session, clock=lambda: now)
    await subs.create_free_subscription(user.id, now)
    pro = await plan(db_session, "pro")

    first = await subs.activate_paid_plan(user.id, pro, now)
    second = await subs.activate_paid_plan(user.id, pro, now + timedelta(days=1))
    third = await subs.activate_paid_plan(user.id, pro, now + timedelta(days=2))

    assert second.current_period_start == first.current_period_end
    assert third.current_period_start == second.current_period_end
    assert (await subs.get_current(user.id)).id == first.id

    in_second_period = SubscriptionService(
        db_session, clock=lambda: first.current_period_end + timedelta(hours=1)
    )
    assert (await in_second_period.get_current(user.id)).id == second.id


@pytest.mark.asyncio
async def test_switching_paid_plans_replaces_everything_open(db_session: AsyncSession) -> None:
    """Moving to a different paid plan closes the old plan and any queued renewals."""
    user = await make_user(db_session)
    now = utc_now()
    subs = SubscriptionService(db_session, clock=lambda: now)
    await subs.create_free_subscription(user.id, now)
    pro = await plan(db_session, "pro")
    business = await plan(db_session, "business")

    await subs.activate_paid_plan(user.id, pro, now)
    await subs.activate_paid_plan(user.id, pro, now)
    switched = await subs.activate_paid_plan(user.id, business, now)

    active = (
        await db_session.scalars(
            select(SubscriptionModel).where(
                SubscriptionModel.user_id == user.id, SubscriptionModel.status == "active"
            )
        )
    ).all()
    assert [s.id for s in active] == [switched.id]


@pytest.mark.asyncio
async def test_expired_paid_plan_falls_back_to_free(db_session: AsyncSession) -> None:
    """After a paid period ends the user is on a fresh Free subscription."""
    user = await make_user(db_session)
    now = utc_now()
    await SubscriptionService(db_session, clock=lambda: now).create_free_subscription(user.id, now)
    await SubscriptionService(db_session, clock=lambda: now).activate_paid_plan(
        user.id, await plan(db_session, "pro"), now
    )

    after = now + BILLING_PERIOD + timedelta(days=1)
    current = await SubscriptionService(db_session, clock=lambda: after).get_current(user.id)
    assert current.plan.slug == "free"


@pytest.mark.asyncio
async def test_seeding_migrates_legacy_slug_and_is_idempotent(db_session: AsyncSession) -> None:
    """The legacy 'unlimited' plan is renamed to 'business' and seeding can run twice."""
    business = await plan(db_session, "business")
    business.slug = "unlimited"
    await db_session.flush()

    service = PlanService(db_session)
    await service.seed_default_plans()
    await service.seed_default_plans()

    slugs = sorted(p.slug for p in (await db_session.scalars(select(PlanConfigModel))).all())
    assert slugs == ["business", "free", "pro"]
