import uuid

from app.workers.celery_app import celery_app
from app.workers.container import relay_outbox, run_processing_job, runtime


@celery_app.task(bind=True, name="run_processing_job", max_retries=None)
def run_processing_job_task(self, job_id: str) -> str:
    """Run one processing job and reschedule it when the step asks to be polled or retried.

    Retry limits live in the job row, not in Celery, so ``max_retries`` is
    unbounded here and the pipeline decides when a job has failed for good.

    Args:
        job_id: Processing job UUID string.

    Returns:
        ``done`` once the job finished.
    """
    outcome = runtime.run(lambda http_client: run_processing_job(uuid.UUID(job_id), http_client))
    if outcome.retry_in is not None:
        raise self.retry(countdown=outcome.retry_in)
    return "done"


@celery_app.task(name="dispatch_outbox")
def dispatch_outbox_task() -> int:
    """Publish pending outbox rows; scheduled by Celery beat every two seconds.

    Returns:
        Number of tasks published.
    """
    return runtime.run(lambda _http_client: relay_outbox())
