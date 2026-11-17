from app.services.export.document import MeetingDocument
from app.services.export.timecode import format_timestamp


class TxtRenderer:
    """Plain-text minutes with summary, action items and transcript."""

    format = "txt"
    media_type = "text/plain; charset=utf-8"
    extension = "txt"

    def render(self, doc: MeetingDocument) -> bytes:
        lines = [
            f"BIÊN BẢN CUỘC HỌP: {doc.title.upper()}",
            "=" * 60,
            f"Thời gian tạo: {doc.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Thời lượng: {doc.duration_seconds:.1f} giây",
            "",
        ]
        if doc.executive_summary:
            lines.extend(["TÓM TẮT ĐIỀU HÀNH:", "-" * 40, doc.executive_summary, ""])
        if doc.action_items:
            lines.extend(["DANH SÁCH VIỆC CẦN LÀM (ACTION ITEMS):", "-" * 40])
            for index, item in enumerate(doc.action_items, 1):
                mark = "[x]" if item.status == "completed" else "[ ]"
                lines.append(f"{index}. {mark} {item.description} (Phụ trách: {item.assignee})")
            lines.append("")
        lines.extend(["NỘI DUNG PHIÊN ÂM CHI TIẾT:", "-" * 40])
        for segment in doc.segments:
            stamp = format_timestamp(segment.start, ms_separator=".")[:8]
            lines.append(f"[{stamp}] {segment.speaker}: {segment.text}")
        return "\n".join(lines).encode("utf-8")
