from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "meeting_tasks",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(name="process_audio_task")
def process_audio_task(meeting_id: str, file_path: str) -> dict[str, str]:
    """Background task to orchestrate diarization, ASR, and summarization.

    Args:
        meeting_id: Unique identifier of the meeting.
        file_path: Local filesystem path to the uploaded audio file.

    Returns:
        Dictionary indicating status.
    """
    return {"meeting_id": meeting_id, "status": "processing_queued"}
