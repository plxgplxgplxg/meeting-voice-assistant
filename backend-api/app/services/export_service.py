import io
import json
import uuid
from datetime import datetime
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meeting import MeetingModel
from app.models.summary import ActionItemModel, SummaryModel
from app.models.transcript import TranscriptSegmentModel


def format_timestamp(seconds: float, separator: str = ":", ms_separator: str = ",") -> str:
    """Format seconds into HH:MM:SS,mmm or HH:MM:SS.mmm format.

    Args:
        seconds: Float seconds.
        separator: Time unit delimiter (default ':').
        ms_separator: Milliseconds delimiter (default ',').

    Returns:
        Formatted timestamp string.
    """
    total_ms = max(0, int(round(seconds * 1000)))
    hours = total_ms // 3_600_000
    minutes = (total_ms % 3_600_000) // 60_000
    secs = (total_ms % 60_000) // 1000
    ms = total_ms % 1000

    return (
        f"{hours:02d}{separator}{minutes:02d}{separator}{secs:02d}"
        f"{ms_separator}{ms:03d}"
    )


class ExportService:
    """Service rendering meeting transcripts and summaries in DOCX, TXT, SRT, VTT, and JSON."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def export_meeting(
        self, meeting_id: uuid.UUID, export_type: str
    ) -> tuple[bytes, str, str]:
        """Export meeting content in the requested format.

        Args:
            meeting_id: Target meeting UUID.
            export_type: Format string ('docx', 'txt', 'srt', 'vtt', 'json').

        Returns:
            Tuple of (file_bytes, media_type, file_extension).

        Raises:
            HTTPException: If meeting not found or unsupported format.
        """
        meeting = await self.session.get(MeetingModel, meeting_id)
        if not meeting or meeting.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found."
            )

        # Retrieve segments in sequence order
        seg_stmt = (
            select(TranscriptSegmentModel)
            .where(TranscriptSegmentModel.meeting_id == meeting_id)
            .order_by(TranscriptSegmentModel.sequence_order.asc())
        )
        segments = list((await self.session.execute(seg_stmt)).scalars().all())

        # Retrieve summary if exists
        summary = await self.session.scalar(
            select(SummaryModel).where(SummaryModel.meeting_id == meeting_id)
        )

        # Retrieve action items if exists
        actions_stmt = (
            select(ActionItemModel)
            .where(ActionItemModel.meeting_id == meeting_id)
            .order_by(ActionItemModel.created_at.asc())
        )
        action_items = list((await self.session.execute(actions_stmt)).scalars().all())

        normalized_type = export_type.lower().strip()

        if normalized_type == "txt":
            content = self._render_txt(meeting, segments, summary, action_items)
            return content.encode("utf-8"), "text/plain; charset=utf-8", "txt"

        if normalized_type == "srt":
            content = self._render_srt(segments)
            return content.encode("utf-8"), "text/plain; charset=utf-8", "srt"

        if normalized_type == "vtt":
            content = self._render_vtt(segments)
            return content.encode("utf-8"), "text/vtt; charset=utf-8", "vtt"

        if normalized_type == "json":
            content = self._render_json(meeting, segments, summary, action_items)
            return json.dumps(content, ensure_ascii=False, indent=2).encode("utf-8"), "application/json", "json"

        if normalized_type == "docx":
            docx_bytes = self._render_docx(meeting, segments, summary, action_items)
            return (
                docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "docx",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported export type '{export_type}'. Supported: txt, docx, srt, vtt, json.",
        )

    def _render_txt(
        self,
        meeting: MeetingModel,
        segments: list[TranscriptSegmentModel],
        summary: SummaryModel | None,
        actions: list[ActionItemModel],
    ) -> str:
        lines = [
            f"BIÊN BẢN CUỘC HỌP: {meeting.title.upper()}",
            "=" * 60,
            f"Thời gian tạo: {meeting.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Thời lượng: {meeting.duration_seconds:.1f} giây",
            "",
        ]

        if summary and summary.executive_summary:
            lines.extend([
                "TÓM TẮT ĐIỀU HÀNH:",
                "-" * 40,
                summary.executive_summary,
                "",
            ])

        if actions:
            lines.extend([
                "DANH SÁCH VIỆC CẦN LÀM (ACTION ITEMS):",
                "-" * 40,
            ])
            for i, act in enumerate(actions, 1):
                status_str = "[x]" if act.status == "completed" else "[ ]"
                lines.append(f"{i}. {status_str} {act.description} (Phụ trách: {act.assignee})")
            lines.append("")

        lines.extend([
            "NỘI DUNG PHIÊN ÂM CHI TIẾT:",
            "-" * 40,
        ])
        for seg in segments:
            ts = f"[{format_timestamp(seg.start_time, ms_separator='.')[:8]}]"
            lines.append(f"{ts} {seg.speaker_label}: {seg.content}")

        return "\n".join(lines)

    def _render_srt(self, segments: list[TranscriptSegmentModel]) -> str:
        entries = []
        for i, seg in enumerate(segments, 1):
            start = format_timestamp(seg.start_time, ms_separator=",")
            end = format_timestamp(seg.end_time, ms_separator=",")
            entries.append(f"{i}\n{start} --> {end}\n[{seg.speaker_label}] {seg.content}\n")
        return "\n".join(entries)

    def _render_vtt(self, segments: list[TranscriptSegmentModel]) -> str:
        entries = ["WEBVTT\n"]
        for seg in segments:
            start = format_timestamp(seg.start_time, ms_separator=".")
            end = format_timestamp(seg.end_time, ms_separator=".")
            entries.append(f"{start} --> {end}\n<v {seg.speaker_label}>{seg.content}\n")
        return "\n".join(entries)

    def _render_json(
        self,
        meeting: MeetingModel,
        segments: list[TranscriptSegmentModel],
        summary: SummaryModel | None,
        actions: list[ActionItemModel],
    ) -> dict:
        return {
            "meeting_id": str(meeting.id),
            "title": meeting.title,
            "status": meeting.status,
            "duration_seconds": meeting.duration_seconds,
            "created_at": meeting.created_at.isoformat(),
            "summary": summary.executive_summary if summary else None,
            "key_points": summary.key_points if summary else [],
            "action_items": [
                {
                    "id": str(a.id),
                    "description": a.description,
                    "assignee": a.assignee,
                    "status": a.status,
                }
                for a in actions
            ],
            "transcript": [
                {
                    "id": str(s.id),
                    "speaker": s.speaker_label,
                    "start": s.start_time,
                    "end": s.end_time,
                    "text": s.content,
                }
                for s in segments
            ],
        }

    def _render_docx(
        self,
        meeting: MeetingModel,
        segments: list[TranscriptSegmentModel],
        summary: SummaryModel | None,
        actions: list[ActionItemModel],
    ) -> bytes:
        doc = Document()

        # Document Title
        title_para = doc.add_paragraph()
        title_run = title_para.add_run(f"BIÊN BẢN CUỘC HỌP\n{meeting.title}")
        title_run.bold = True
        title_run.font.size = Pt(18)
        title_run.font.color.rgb = RGBColor(15, 23, 42)  # Slate-900
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Metadata Table
        meta_table = doc.add_table(rows=2, cols=2)
        meta_table.style = "Table Grid"
        meta_table.cell(0, 0).text = f"Ngày tạo: {meeting.created_at.strftime('%d/%m/%Y %H:%M')}"
        meta_table.cell(0, 1).text = f"Thời lượng: {meeting.duration_seconds / 60:.1f} phút"
        meta_table.cell(1, 0).text = f"Mã cuộc họp: {str(meeting.id)[:8]}"
        meta_table.cell(1, 1).text = f"Số lượt phát biểu: {len(segments)}"

        doc.add_paragraph()  # Spacing

        # Summary Section
        if summary and summary.executive_summary:
            h2 = doc.add_heading("1. Tóm Tắt Điều Hành (Executive Summary)", level=2)
            h2.style.font.color.rgb = RGBColor(5, 150, 105)  # Emerald-600
            doc.add_paragraph(summary.executive_summary)

        # Action Items Section
        if actions:
            h2 = doc.add_heading("2. Việc Cần Làm (Action Items)", level=2)
            h2.style.font.color.rgb = RGBColor(5, 150, 105)
            act_table = doc.add_table(rows=1, cols=3)
            act_table.style = "Table Grid"
            hdr_cells = act_table.rows[0].cells
            hdr_cells[0].text = "Nhiệm vụ"
            hdr_cells[1].text = "Người phụ trách"
            hdr_cells[2].text = "Trạng thái"

            for a in actions:
                row_cells = act_table.add_row().cells
                row_cells[0].text = a.description
                row_cells[1].text = a.assignee
                row_cells[2].text = "Hoàn thành" if a.status == "completed" else "Đang chờ"

            doc.add_paragraph()

        # Transcript Section
        h2 = doc.add_heading("3. Biên Bản Chi Tiết Theo Người Nói", level=2)
        h2.style.font.color.rgb = RGBColor(5, 150, 105)

        t_table = doc.add_table(rows=1, cols=3)
        t_table.style = "Table Grid"
        t_hdr = t_table.rows[0].cells
        t_hdr[0].text = "Thời gian"
        t_hdr[1].text = "Người nói"
        t_hdr[2].text = "Nội dung"

        for s in segments:
            row_cells = t_table.add_row().cells
            row_cells[0].text = f"{format_timestamp(s.start_time, ms_separator='.')[:8]}"
            row_cells[1].text = s.speaker_label
            row_cells[2].text = s.content

        stream = io.BytesIO()
        doc.save(stream)
        return stream.getvalue()
