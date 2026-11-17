import io

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

from app.services.export.document import MeetingDocument
from app.services.export.timecode import format_timestamp

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
HEADING_COLOR = RGBColor(5, 150, 105)


class DocxRenderer:
    """Word minutes with summary, action items table and transcript table."""

    format = "docx"
    media_type = DOCX_MEDIA_TYPE
    extension = "docx"

    def render(self, doc: MeetingDocument) -> bytes:
        document = Document()

        title = document.add_paragraph()
        run = title.add_run(f"BIÊN BẢN CUỘC HỌP\n{doc.title}")
        run.bold = True
        run.font.size = Pt(18)
        run.font.color.rgb = RGBColor(15, 23, 42)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        meta = document.add_table(rows=2, cols=2)
        meta.style = "Table Grid"
        meta.cell(0, 0).text = f"Ngày tạo: {doc.created_at.strftime('%d/%m/%Y %H:%M')}"
        meta.cell(0, 1).text = f"Thời lượng: {doc.duration_seconds / 60:.1f} phút"
        meta.cell(1, 0).text = f"Mã cuộc họp: {str(doc.meeting_id)[:8]}"
        meta.cell(1, 1).text = f"Số lượt phát biểu: {len(doc.segments)}"
        document.add_paragraph()

        if doc.executive_summary:
            heading = document.add_heading("1. Tóm Tắt Điều Hành (Executive Summary)", level=2)
            heading.style.font.color.rgb = HEADING_COLOR
            document.add_paragraph(doc.executive_summary)

        if doc.action_items:
            heading = document.add_heading("2. Việc Cần Làm (Action Items)", level=2)
            heading.style.font.color.rgb = HEADING_COLOR
            table = document.add_table(rows=1, cols=3)
            table.style = "Table Grid"
            headers = ("Nhiệm vụ", "Người phụ trách", "Trạng thái")
            for cell, label in zip(table.rows[0].cells, headers, strict=True):
                cell.text = label
            for item in doc.action_items:
                cells = table.add_row().cells
                cells[0].text = item.description
                cells[1].text = item.assignee
                cells[2].text = "Hoàn thành" if item.status == "completed" else "Đang chờ"
            document.add_paragraph()

        heading = document.add_heading("3. Biên Bản Chi Tiết Theo Người Nói", level=2)
        heading.style.font.color.rgb = HEADING_COLOR
        table = document.add_table(rows=1, cols=3)
        table.style = "Table Grid"
        for cell, label in zip(table.rows[0].cells, ("Thời gian", "Người nói", "Nội dung"), strict=True):
            cell.text = label
        for segment in doc.segments:
            cells = table.add_row().cells
            cells[0].text = format_timestamp(segment.start, ms_separator=".")[:8]
            cells[1].text = segment.speaker
            cells[2].text = segment.text

        stream = io.BytesIO()
        document.save(stream)
        return stream.getvalue()
