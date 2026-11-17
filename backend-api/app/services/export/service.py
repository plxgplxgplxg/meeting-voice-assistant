from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationFailedError
from app.models.billing import PlanConfigModel
from app.models.meeting import MeetingModel
from app.services.billing.plan_service import PlanService
from app.services.billing.subscription_service import SubscriptionService
from app.services.export.document import MeetingDocument, MeetingDocumentLoader
from app.services.export.registry import ExportRegistry, build_default_registry


class ExportService:
    """Renders meetings through the export registry, gated by the owner's plan."""

    def __init__(
        self,
        session: AsyncSession,
        registry: ExportRegistry | None = None,
        loader: MeetingDocumentLoader | None = None,
        plan_service: PlanService | None = None,
        subscription_service: SubscriptionService | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            session: Active SQLAlchemy session.
            registry: Available renderers; defaults to the built-in set.
            loader: Builds the meeting read model.
            plan_service: Plan gating collaborator.
            subscription_service: Resolves the plan of the meeting owner.
        """
        self.session = session
        self.registry = registry or build_default_registry()
        self.loader = loader or MeetingDocumentLoader(session)
        self.plan_service = plan_service or PlanService(session)
        self.subscription_service = subscription_service or SubscriptionService(session)

    async def export_meeting(
        self, meeting: MeetingModel, export_type: str
    ) -> tuple[bytes, str, str]:
        """Export meeting content in the requested format.

        The format must be included in the plan of the meeting owner, so a guest
        opening a share link can export what the owner has paid for.

        Args:
            meeting: Meeting already authorized for viewing.
            export_type: Registered format name.

        Returns:
            Tuple of (file_bytes, media_type, file_extension).

        Raises:
            ValidationFailedError: If the format is unsupported.
            QuotaExceededError: If the owner's plan excludes the format.
        """
        renderer = self.registry.get(export_type)
        self.plan_service.assert_export_format_allowed(
            await self._owner_plan(meeting), renderer.format
        )
        document = await self.loader.load(meeting)
        return renderer.render(document), renderer.media_type, renderer.extension

    async def load_document(self, meeting: MeetingModel) -> MeetingDocument:
        """Return the read model of a meeting, for callers that render it themselves."""
        return await self.loader.load(meeting)

    async def _owner_plan(self, meeting: MeetingModel) -> PlanConfigModel:
        if meeting.created_by is not None:
            return (await self.subscription_service.get_current(meeting.created_by)).plan
        free_plan = await self.plan_service.get_plan_by_slug("free")
        if free_plan is None:
            raise ValidationFailedError("Free plan is not configured.", code="PLAN_NOT_CONFIGURED")
        return free_plan
