import io
import re

from docx import Document
from docx.text.paragraph import Paragraph

HEADING_PATTERN = re.compile(r"^(#{1,3})\s+(.*)$")
BULLET_PATTERN = re.compile(r"^\s*[-*]\s+(.*)$")
NUMBERED_PATTERN = re.compile(r"^\s*\d+[.)]\s+(.*)$")
BOLD_PATTERN = re.compile(r"(\*\*[^*]+\*\*)")


def _add_runs(paragraph: Paragraph, text: str) -> None:
    """Add text to a paragraph, rendering ``**bold**`` spans."""
    for part in BOLD_PATTERN.split(text):
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            paragraph.add_run(part[2:-2]).bold = True
        elif part:
            paragraph.add_run(part)


def markdown_to_docx(title: str, markdown: str) -> bytes:
    """Convert a small subset of Markdown into a Word document.

    Supports ``#``-``###`` headings, ``-``/``*`` bullets, numbered lists, ``**bold**``
    and plain paragraphs. Anything else is kept as literal paragraph text, so
    untrusted content can never inject markup into the file.

    Args:
        title: Document title shown as the first heading.
        markdown: Markdown body.

    Returns:
        The ``.docx`` file content.
    """
    document = Document()
    document.add_heading(title, level=0)
    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if match := HEADING_PATTERN.match(line):
            document.add_heading(match.group(2), level=len(match.group(1)))
        elif match := BULLET_PATTERN.match(line):
            _add_runs(document.add_paragraph(style="List Bullet"), match.group(1))
        elif match := NUMBERED_PATTERN.match(line):
            _add_runs(document.add_paragraph(style="List Number"), match.group(1))
        else:
            _add_runs(document.add_paragraph(), line)
    stream = io.BytesIO()
    document.save(stream)
    return stream.getvalue()
