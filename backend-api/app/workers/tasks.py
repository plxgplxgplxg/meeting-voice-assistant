import uuid

from app.workers.celery_app import celery_app
from app.workers.container import run_meeting_pipeline, runtime


@celery_app.task(name="process_meeting_task")
def process_meeting_task(meeting_id: str, audio_file_id: str) -> str:
    """Process an uploaded recording: transcribe, summarize, and charge quota.

    Args:
        meeting_id: Meeting UUID string.
        audio_file_id: Audio file UUID string.

    Returns:
        Final meeting status value.
    """
    return runtime.run(
        lambda http_client: run_meeting_pipeline(
            uuid.UUID(meeting_id), uuid.UUID(audio_file_id), http_client
        )
    )
