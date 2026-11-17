from app.services.export.document import MeetingDocument
from app.services.export.timecode import format_timestamp


class SrtRenderer:
    """SubRip subtitles with the speaker in square brackets."""

    format = "srt"
    media_type = "text/plain; charset=utf-8"
    extension = "srt"

    def render(self, doc: MeetingDocument) -> bytes:
        entries = []
        for index, segment in enumerate(doc.segments, 1):
            start = format_timestamp(segment.start, ms_separator=",")
            end = format_timestamp(segment.end, ms_separator=",")
            entries.append(f"{index}\n{start} --> {end}\n[{segment.speaker}] {segment.text}\n")
        return "\n".join(entries).encode("utf-8")
