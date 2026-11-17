from app.services.export.document import MeetingDocument
from app.services.export.timecode import format_timestamp


class VttRenderer:
    """WebVTT subtitles with voice tags."""

    format = "vtt"
    media_type = "text/vtt; charset=utf-8"
    extension = "vtt"

    def render(self, doc: MeetingDocument) -> bytes:
        entries = ["WEBVTT\n"]
        for segment in doc.segments:
            start = format_timestamp(segment.start, ms_separator=".")
            end = format_timestamp(segment.end, ms_separator=".")
            entries.append(f"{start} --> {end}\n<v {segment.speaker}>{segment.text}\n")
        return "\n".join(entries).encode("utf-8")
