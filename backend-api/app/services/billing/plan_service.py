from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import QuotaExceededError
from app.models.billing import PlanConfigModel

LEGACY_PLAN_SLUGS: dict[str, str] = {"unlimited": "business"}

DEFAULT_PLANS: tuple[dict[str, Any], ...] = (
    {
        "slug": "free",
        "name": "Gói Miễn Phí",
        "description": "Trải nghiệm trợ lý cuộc họp với thời lượng cơ bản.",
        "price_amount": Decimal("0"),
        "total_duration_limit_minutes": 60,
        "is_default": True,
        "features": {
            "max_meetings": 5,
            "export_formats": ["txt", "json"],
            "rag_questions": 20,
            "priority_gpu": False,
        },
    },
    {
        "slug": "pro",
        "name": "Gói Chuyên Nghiệp",
        "description": "Dành cho chuyên viên và nhóm làm việc thường xuyên họp trực tuyến.",
        "price_amount": Decimal("99000"),
        "total_duration_limit_minutes": 600,
        "is_default": False,
        "features": {
            "max_meetings": "unlimited",
            "export_formats": ["docx", "txt", "srt", "vtt", "json"],
            "rag_questions": "unlimited",
            "priority_gpu": True,
            "speaker_diarization": True,
        },
    },
    {
        "slug": "business",
        "name": "Gói Doanh Nghiệp",
        "description": "Toàn bộ tính năng cao cấp không giới hạn thời lượng.",
        "price_amount": Decimal("299000"),
        "total_duration_limit_minutes": 0,
        "is_default": False,
        "features": {
            "max_meetings": "unlimited",
            "export_formats": ["docx", "txt", "srt", "vtt", "json"],
            "rag_questions": "unlimited",
            "priority_gpu": True,
            "speaker_diarization": True,
            "workspace_collaboration": True,
        },
    },
)


def is_free_plan(plan: PlanConfigModel) -> bool:
    """Return whether a plan costs nothing and therefore rolls over monthly.

    Args:
        plan: Plan configuration to inspect.

    Returns:
        True for the zero-price plan.
    """
    return plan.price_amount <= 0


class PlanService:
    """Service managing subscription plan tiers and plan feature gating."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def seed_default_plans(self) -> None:
        """Create any missing default plans and migrate legacy plan slugs.

        Called from application startup only. Read paths never seed so GET
        requests have no side effects.
        """
        existing = {
            plan.slug: plan
            for plan in (await self.session.execute(select(PlanConfigModel))).scalars()
        }
        for legacy_slug, new_slug in LEGACY_PLAN_SLUGS.items():
            legacy = existing.pop(legacy_slug, None)
            if legacy and new_slug not in existing:
                legacy.slug = new_slug
                existing[new_slug] = legacy

        for spec in DEFAULT_PLANS:
            if spec["slug"] not in existing:
                self.session.add(PlanConfigModel(currency="VND", billing_interval="monthly", **spec))
        await self.session.flush()

    async def list_active_plans(self) -> Sequence[PlanConfigModel]:
        """List all publicly active plan configurations ordered by price."""
        result = await self.session.execute(
            select(PlanConfigModel)
            .where(PlanConfigModel.is_active.is_(True))
            .order_by(PlanConfigModel.price_amount.asc())
        )
        return result.scalars().all()

    async def get_plan_by_slug(self, slug: str) -> PlanConfigModel | None:
        """Find an active plan configuration by its unique slug."""
        result = await self.session.execute(
            select(PlanConfigModel).where(
                PlanConfigModel.slug == slug.lower().strip(),
                PlanConfigModel.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    def assert_export_format_allowed(self, plan: PlanConfigModel, export_format: str) -> None:
        """Ensure a plan includes the requested export format.

        Args:
            plan: Plan of the meeting owner.
            export_format: Lower-case export format identifier.

        Raises:
            QuotaExceededError: With code ``PLAN_FEATURE_REQUIRED`` when the plan excludes the format.
        """
        allowed = plan.features.get("export_formats", [])
        if export_format not in allowed:
            raise QuotaExceededError(
                f"Export format '{export_format}' is not included in the {plan.name} plan. "
                "Please upgrade to use it.",
                code="PLAN_FEATURE_REQUIRED",
            )
