import uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TranscriptEdited:
    """A user or agent changed transcript segments through the editor.

    Attributes:
        meeting_id: Meeting whose transcript changed.
        revision: Transcript revision after the change.
        change_set_id: Change set recording the edit.
    """

    meeting_id: uuid.UUID
    revision: int
    change_set_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class TranscriptReplaced:
    """The whole transcript was replaced by a fresh transcription.

    Attributes:
        meeting_id: Meeting whose transcript was replaced.
        revision: Transcript revision after the replacement.
        audio_file_id: Recording the new transcript came from.
    """

    meeting_id: uuid.UUID
    revision: int
    audio_file_id: uuid.UUID | None


DomainEvent = TranscriptEdited | TranscriptReplaced
