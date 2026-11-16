import uuid
from collections.abc import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import PlanConfigModel


class PlanService:
    """Service managing subscription plan tiers and default seeding."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def seed_default_plans_if_empty(self) -> None:
        """Seed Free, Pro, and Unlimited plan configs if none exist in the database."""
        result = await self.session.execute(select(PlanConfigModel))
        if result.first():
            return

        default_plans = [
            PlanConfigModel(
                slug="free",
                name="Gói Miễn Phí",
                description="Trải nghiệm trợ lý cuộc họp với thời lượng cơ bản.",
                price_amount=0.0,
                currency="VND",
                billing_interval="monthly",
                total_duration_limit_minutes=60,
                features={
                    "max_meetings": 5,
                    "export_formats": ["txt", "json"],
                    "rag_questions": 20,
                    "priority_gpu": False,
                },
                is_default=True,
                is_active=True,
            ),
            PlanConfigModel(
                slug="pro",
                name="Gói Chuyên Nghiệp",
                description="Dành cho chuyên viên và nhóm làm việc thường xuyên họp trực tuyến.",
                price_amount=99000.0,
                currency="VND",
                billing_interval="monthly",
                total_duration_limit_minutes=600,
                features={
                    "max_meetings": "unlimited",
                    "export_formats": ["docx", "txt", "srt", "vtt", "json"],
                    "rag_questions": "unlimited",
                    "priority_gpu": True,
                    "speaker_diarization": True,
                },
                is_default=False,
                is_active=True,
            ),
            PlanConfigModel(
                slug="unlimited",
                name="Gói Vô Hạn",
                description="Toàn bộ tính năng cao cấp không giới hạn thời lượng.",
                price_amount=299000.0,
                currency="VND",
                billing_interval="monthly",
                total_duration_limit_minutes=0,  # 0 indicates unlimited
                features={
                    "max_meetings": "unlimited",
                    "export_formats": ["docx", "txt", "srt", "vtt", "json"],
                    "rag_questions": "unlimited",
                    "priority_gpu": True,
                    "speaker_diarization": True,
                    "workspace_collaboration": True,
                },
                is_default=False,
                is_active=True,
            ),
        ]

        self.session.add_all(default_plans)
        await self.session.flush()

    async def list_active_plans(self) -> Sequence[PlanConfigModel]:
        """List all publicly active plan configurations."""
        await self.seed_default_plans_if_empty()
        result = await self.session.execute(
            select(PlanConfigModel)
            .where(PlanConfigModel.is_active == True)
            .order_by(PlanConfigModel.price_amount.asc())
        )
        return result.scalars().all()

    async def get_plan_by_slug(self, slug: str) -> PlanConfigModel | None:
        """Find a plan configuration by its unique slug."""
        await self.seed_default_plans_if_empty()
        result = await self.session.execute(
            select(PlanConfigModel).where(
                PlanConfigModel.slug == slug.lower().strip(),
                PlanConfigModel.is_active == True,
            )
        )
        return result.scalar_one_or_none()
