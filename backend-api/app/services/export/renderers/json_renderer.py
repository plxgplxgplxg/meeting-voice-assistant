import json

from app.services.export.document import MeetingDocument


class JsonRenderer:
    """Structured JSON export for integrations."""

    format = "json"
    media_type = "application/json"
    extension = "json"

    def render(self, doc: MeetingDocument) -> bytes:
        payload = {
            "meeting_id": str(doc.meeting_id),
            "title": doc.title,
            "status": doc.status,
            "duration_seconds": doc.duration_seconds,
            "created_at": doc.created_at.isoformat(),
            "summary": doc.executive_summary,
            "key_points": doc.key_points,
            "action_items": [
                {
                    "id": str(a.id),
                    "description": a.description,
                    "assignee": a.assignee,
                    "status": a.status,
                }
                for a in doc.action_items
            ],
            "transcript": [
                {
                    "id": str(s.id),
                    "speaker": s.speaker,
                    "start": s.start,
                    "end": s.end,
                    "text": s.text,
                }
                for s in doc.segments
            ],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
