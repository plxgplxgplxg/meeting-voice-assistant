import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utc_now
from app.core.errors import QuotaExceededError
from app.models.agent import AgentConversationModel, AgentMessageModel
from app.models.billing import MeetingQuotaUsageModel, SubscriptionModel
from app.models.user import UserModel
from app.schemas.billing import SubscriptionResponse
from app.services.billing.plan_service import PlanService
from app.services.billing.subscription_service import SubscriptionService

UNLIMITED_REMAINING_MINUTES = 999999.0


class QuotaService:
    """Service tracking audio duration usage and asserting plan quota limits."""

    def __init__(
        self,
        session: AsyncSession,
        subscriptions: SubscriptionService | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            session: Active SQLAlchemy session.
            subscriptions: Subscription service; defaults to one on ``session``.
        """
        self.session = session
        self.subscriptions = subscriptions or SubscriptionService(session)

    async def get_user_subscription_summary(self, user: UserModel) -> SubscriptionResponse:
        """Calculate the user's subscription, used minutes, and remaining quota.

        Args:
            user: Account to summarize.

        Returns:
            Subscription summary for the current billing period.
        """
        sub = await self.subscriptions.get_current(user.id)
        used_minutes = round(await self._used_seconds(user.id, sub) / 60.0, 1)

        limit_minutes = sub.plan.total_duration_limit_minutes
        if limit_minutes == 0:
            remaining_minutes = UNLIMITED_REMAINING_MINUTES
        else:
            remaining_minutes = max(0.0, round(limit_minutes - used_minutes, 1))

        return SubscriptionResponse(
            id=sub.id,
            plan_slug=sub.plan.slug,
            plan_name=sub.plan.name,
            status=sub.status,
            current_period_end=sub.current_period_end,
            total_duration_limit_minutes=limit_minutes,
            used_duration_minutes=used_minutes,
            remaining_duration_minutes=remaining_minutes,
        )

    async def assert_within_quota(self, user: UserModel) -> None:
        """Verify the user still has quota before accepting a recording.

        Args:
            user: Account about to upload audio.

        Raises:
            QuotaExceededError: If the current period's quota is exhausted.
        """
        summary = await self.get_user_subscription_summary(user)
        if summary.total_duration_limit_minutes > 0 and summary.remaining_duration_minutes <= 0:
            raise QuotaExceededError(
                f"Monthly recording quota exhausted ({summary.used_duration_minutes}/"
                f"{summary.total_duration_limit_minutes} minutes). Please upgrade your plan."
            )

    async def assert_agent_allowed(self, user_id: uuid.UUID) -> None:
        """Ensure the user's plan includes assistant edits and generated documents.

        Args:
            user_id: User about to use an agent write tool or create an artifact.

        Raises:
            QuotaExceededError: With code ``PLAN_FEATURE_REQUIRED`` on plans without agent tools.
        """
        sub = await self.subscriptions.get_current(user_id)
        PlanService(self.session).assert_agent_allowed(sub.plan)

    async def agent_tools_enabled(self, user_id: uuid.UUID) -> bool:
        """Return whether the user's plan includes the assistant's tools."""
        sub = await self.subscriptions.get_current(user_id)
        return bool(sub.plan.features.get("agent_tools"))

    async def assert_question_allowed(self, user_id: uuid.UUID) -> None:
        """Enforce the plan's monthly question limit (``features.rag_questions``).

        Args:
            user_id: User about to ask a question.

        Raises:
            QuotaExceededError: With code ``RAG_QUESTION_LIMIT`` once the limit is used up.
        """
        sub = await self.subscriptions.get_current(user_id)
        limit = sub.plan.features.get("rag_questions")
        if not isinstance(limit, int):
            return
        used = await self.session.scalar(
            select(func.count())
            .select_from(AgentMessageModel)
            .join(
                AgentConversationModel,
                AgentConversationModel.id == AgentMessageModel.conversation_id,
            )
            .where(
                AgentConversationModel.user_id == user_id,
                AgentMessageModel.role == "user",
                AgentMessageModel.created_at >= sub.current_period_start,
                AgentMessageModel.created_at < sub.current_period_end,
            )
        )
        if (used or 0) >= limit:
            raise QuotaExceededError(
                f"Monthly question limit reached ({limit}). Please upgrade your plan.",
                code="RAG_QUESTION_LIMIT",
            )

    async def record_usage(
        self,
        user_id: uuid.UUID,
        meeting_id: uuid.UUID | None,
        duration_seconds: float,
        audio_file_id: uuid.UUID | None = None,
    ) -> bool:
        """Record audio duration consumed by a successfully processed recording.

        Recording is idempotent per ``audio_file_id`` so reprocessing the same
        file never charges twice.

        Args:
            user_id: Account being charged.
            meeting_id: Meeting the audio belongs to.
            duration_seconds: Probed audio duration.
            audio_file_id: Idempotency key for the audio file.

        Returns:
            True when a usage row was written, False when skipped.
        """
        if duration_seconds <= 0:
            return False

        if audio_file_id is not None:
            already_charged = await self.session.scalar(
                select(MeetingQuotaUsageModel.id).where(
                    MeetingQuotaUsageModel.audio_file_id == audio_file_id
                )
            )
            if already_charged:
                return False

        self.session.add(
            MeetingQuotaUsageModel(
                user_id=user_id,
                meeting_id=meeting_id,
                audio_file_id=audio_file_id,
                duration_seconds=duration_seconds,
                usage_at=utc_now(),
            )
        )
        await self.session.flush()
        return True

    async def _used_seconds(self, user_id: uuid.UUID, sub: SubscriptionModel) -> float:
        total = await self.session.scalar(
            select(func.coalesce(func.sum(MeetingQuotaUsageModel.duration_seconds), 0.0)).where(
                MeetingQuotaUsageModel.user_id == user_id,
                MeetingQuotaUsageModel.usage_at >= sub.current_period_start,
                MeetingQuotaUsageModel.usage_at < sub.current_period_end,
            )
        )
        return float(total or 0.0)
