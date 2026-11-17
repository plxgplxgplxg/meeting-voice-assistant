from datetime import timedelta
from typing import Any, Protocol

import structlog
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utc_now
from app.models.outbox import OutboxEventModel

logger = structlog.get_logger(__name__)

DEFAULT_BATCH_SIZE = 50


class TaskSender(Protocol):
    """Seam for publishing a task to the message broker."""

    def send(self, task_name: str, args: list[Any]) -> None:
        """Publish a task.

        Args:
            task_name: Registered task name.
            args: JSON-serializable positional arguments.
        """
        ...


class CeleryTaskSender:
    """Publishes tasks through the Celery app."""

    def send(self, task_name: str, args: list[Any]) -> None:
        from app.workers.celery_app import celery_app

        celery_app.send_task(task_name, args=args)


class OutboxService:
    """Writes tasks to the outbox inside the caller's transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def enqueue(
        self, task_name: str, args: list[Any], delay_seconds: float = 0
    ) -> OutboxEventModel:
        """Record a task to be published after the transaction commits.

        Args:
            task_name: Registered task name.
            args: JSON-serializable positional arguments.
            delay_seconds: Hold the task back this long, which debounces bursts of edits.

        Returns:
            The pending outbox row.
        """
        available_at = utc_now() + timedelta(seconds=delay_seconds) if delay_seconds else None
        event = OutboxEventModel(
            task_name=task_name, payload={"args": args}, available_at=available_at
        )
        self.session.add(event)
        await self.session.flush()
        return event


class OutboxRelay:
    """Publishes pending outbox rows to the broker."""

    def __init__(self, session: AsyncSession, sender: TaskSender) -> None:
        """Initialize the relay.

        Args:
            session: Session owned by the polling task; the caller commits.
            sender: Broker publisher.
        """
        self.session = session
        self.sender = sender

    async def dispatch_pending(self, batch_size: int = DEFAULT_BATCH_SIZE) -> int:
        """Publish undispatched rows, oldest first.

        Rows are claimed with ``FOR UPDATE SKIP LOCKED`` so several relays can run
        without double-sending. A publish failure leaves the row pending for the
        next poll, which is what survives a broker outage.

        Args:
            batch_size: Maximum rows to publish in one call.

        Returns:
            Number of rows published.
        """
        rows = (
            await self.session.scalars(
                select(OutboxEventModel)
                .where(
                    OutboxEventModel.dispatched_at.is_(None),
                    or_(
                        OutboxEventModel.available_at.is_(None),
                        OutboxEventModel.available_at <= utc_now(),
                    ),
                )
                .order_by(OutboxEventModel.created_at)
                .limit(batch_size)
                .with_for_update(skip_locked=True)
            )
        ).all()

        sent = 0
        for row in rows:
            row.attempts += 1
            try:
                self.sender.send(row.task_name, list(row.payload.get("args", [])))
            except Exception as exc:
                logger.warning("outbox_publish_failed", event_id=str(row.id), error=str(exc))
                break
            row.dispatched_at = utc_now()
            sent += 1
        await self.session.flush()
        return sent
