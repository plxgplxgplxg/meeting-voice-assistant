import uuid
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationFailedError
from app.models.agent import MeetingArtifactModel
from app.models.meeting import MeetingModel
from app.services.export.document import MeetingDocumentLoader
from app.services.export.markdown_docx import markdown_to_docx
from app.services.export.registry import ExportRegistry, build_default_registry
from app.services.export.renderers.docx import DOCX_MEDIA_TYPE
from app.services.storage_service import StorageService

ArtifactKind = Literal["minutes_docx", "email_draft", "srt", "custom_md"]
MAX_MARKDOWN_CHARS = 200_000
MARKDOWN_MEDIA_TYPE = "text/markdown; charset=utf-8"


@dataclass(frozen=True, slots=True)
class RenderedArtifact:
    """File content produced for an artifact."""

    data: bytes
    media_type: str
    extension: str


class ArtifactService:
    """Generates and stores derived files (minutes, email drafts, subtitles) for a meeting.

    Artifacts are derived data: creating one needs VIEW access, deleting one needs MANAGE.
    Callers authorize before calling.
    """

    def __init__(
        self,
        session: AsyncSession,
        storage: StorageService,
        loader: MeetingDocumentLoader | None = None,
        registry: ExportRegistry | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            session: Active SQLAlchemy session.
            storage: Object storage for the generated files.
            loader: Builds the meeting read model.
            registry: Renderers used for subtitle and default minutes output.
        """
        self.session = session
        self.storage = storage
        self.loader = loader or MeetingDocumentLoader(session)
        self.registry = registry or build_default_registry()

    async def create(
        self,
        meeting: MeetingModel,
        created_by: uuid.UUID | None,
        kind: ArtifactKind,
        title: str,
        content_markdown: str | None = None,
        agent_action_id: uuid.UUID | None = None,
    ) -> MeetingArtifactModel:
        """Render and store an artifact.

        Args:
            meeting: Meeting already authorized for viewing.
            created_by: User the artifact is created for.
            kind: ``minutes_docx``, ``email_draft``, ``srt`` or ``custom_md``.
            title: Display title.
            content_markdown: Body for markdown-based kinds. ``minutes_docx`` without a
                body uses the standard minutes layout.
            agent_action_id: Proposal that led to the artifact, if any.

        Returns:
            The stored artifact record.

        Raises:
            ValidationFailedError: If required content is missing or too large.
        """
        if content_markdown is not None and len(content_markdown) > MAX_MARKDOWN_CHARS:
            raise ValidationFailedError("The document is too large.", code="ARTIFACT_TOO_LARGE")
        rendered = await self._render(meeting, kind, title, content_markdown)

        artifact_id = uuid.uuid4()
        storage_key = f"artifacts/{meeting.id}/{artifact_id}.{rendered.extension}"
        size = await self.storage.save_bytes(storage_key, rendered.data)
        artifact = MeetingArtifactModel(
            id=artifact_id,
            meeting_id=meeting.id,
            created_by=created_by,
            kind=kind,
            title=title.strip(),
            storage_key=storage_key,
            mime_type=rendered.media_type,
            size_bytes=size,
            source_revision=meeting.transcript_revision,
            agent_action_id=agent_action_id,
        )
        self.session.add(artifact)
        await self.session.flush()
        return artifact

    async def list(self, meeting_id: uuid.UUID) -> list[MeetingArtifactModel]:
        """List a meeting's artifacts, newest first."""
        result = await self.session.scalars(
            select(MeetingArtifactModel)
            .where(MeetingArtifactModel.meeting_id == meeting_id)
            .order_by(MeetingArtifactModel.created_at.desc())
        )
        return list(result.all())

    async def get(self, meeting_id: uuid.UUID, artifact_id: uuid.UUID) -> MeetingArtifactModel:
        """Return one artifact of a meeting.

        Raises:
            NotFoundError: If it does not exist in this meeting.
        """
        artifact = await self.session.scalar(
            select(MeetingArtifactModel).where(
                MeetingArtifactModel.id == artifact_id,
                MeetingArtifactModel.meeting_id == meeting_id,
            )
        )
        if artifact is None:
            raise NotFoundError("Artifact not found.", code="ARTIFACT_NOT_FOUND")
        return artifact

    async def delete(self, artifact: MeetingArtifactModel) -> None:
        """Delete the artifact record and its stored file."""
        self.storage.delete(artifact.storage_key)
        await self.session.delete(artifact)
        await self.session.flush()

    async def _render(
        self, meeting: MeetingModel, kind: ArtifactKind, title: str, content_markdown: str | None
    ) -> RenderedArtifact:
        if kind == "srt":
            document = await self.loader.load(meeting)
            renderer = self.registry.get("srt")
            return RenderedArtifact(renderer.render(document), renderer.media_type, "srt")

        if kind == "minutes_docx":
            if content_markdown:
                return RenderedArtifact(
                    markdown_to_docx(title, content_markdown), DOCX_MEDIA_TYPE, "docx"
                )
            document = await self.loader.load(meeting)
            renderer = self.registry.get("docx")
            return RenderedArtifact(renderer.render(document), renderer.media_type, "docx")

        if not content_markdown or not content_markdown.strip():
            raise ValidationFailedError(
                f"'{kind}' needs content_markdown.", code="ARTIFACT_CONTENT_REQUIRED"
            )
        return RenderedArtifact(content_markdown.encode("utf-8"), MARKDOWN_MEDIA_TYPE, "md")
