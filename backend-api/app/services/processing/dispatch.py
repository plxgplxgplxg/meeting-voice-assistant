import uuid
from typing import Protocol


class ProcessingDispatcher(Protocol):
    """Seam for enqueueing background meeting processing."""

    def dispatch(self, meeting_id: uuid.UUID, audio_file_id: uuid.UUID) -> None:
        """Enqueue processing of an uploaded recording.

        Args:
            meeting_id: Meeting to process.
            audio_file_id: Uploaded audio file to transcribe.
        """
        ...


class CeleryProcessingDispatcher:
    """Dispatcher that sends the processing task to the Celery broker."""

    def dispatch(self, meeting_id: uuid.UUID, audio_file_id: uuid.UUID) -> None:
        from app.workers.celery_app import celery_app

        celery_app.send_task("process_meeting_task", args=[str(meeting_id), str(audio_file_id)])
