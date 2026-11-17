from typing import Protocol

from app.core.errors import ValidationFailedError
from app.services.export.document import MeetingDocument


class ExportRenderer(Protocol):
    """Renders a meeting document in one file format.

    Adding a format means adding a renderer and registering it; no existing code
    changes.
    """

    format: str
    media_type: str
    extension: str

    def render(self, doc: MeetingDocument) -> bytes:
        """Render the document.

        Args:
            doc: Meeting read model.

        Returns:
            File content.
        """
        ...


class ExportRegistry:
    """Lookup of renderers by format name."""

    def __init__(self) -> None:
        self._renderers: dict[str, ExportRenderer] = {}

    def register(self, renderer: ExportRenderer) -> None:
        """Register a renderer under its format name.

        Args:
            renderer: Renderer to add.
        """
        self._renderers[renderer.format] = renderer

    @property
    def formats(self) -> tuple[str, ...]:
        """Registered format names."""
        return tuple(self._renderers)

    def get(self, export_format: str) -> ExportRenderer:
        """Return the renderer for a format.

        Args:
            export_format: Format name, case-insensitive.

        Returns:
            The registered renderer.

        Raises:
            ValidationFailedError: If the format is not registered.
        """
        renderer = self._renderers.get(export_format.lower().strip())
        if renderer is None:
            raise ValidationFailedError(
                f"Unsupported export type '{export_format}'. Supported: {', '.join(self.formats)}.",
                code="UNSUPPORTED_EXPORT_FORMAT",
            )
        return renderer


def build_default_registry() -> ExportRegistry:
    """Create the registry with every built-in renderer."""
    from app.services.export.renderers import (
        DocxRenderer,
        JsonRenderer,
        SrtRenderer,
        TxtRenderer,
        VttRenderer,
    )

    registry = ExportRegistry()
    for renderer in (TxtRenderer(), DocxRenderer(), SrtRenderer(), VttRenderer(), JsonRenderer()):
        registry.register(renderer)
    return registry
