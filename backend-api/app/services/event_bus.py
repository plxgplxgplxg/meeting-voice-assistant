from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.events import DomainEvent, TranscriptEdited, TranscriptReplaced

Handler = Callable[[Any], Awaitable[None]]


class EventBus:
    """In-process synchronous event dispatcher.

    Handlers run inside the publisher's transaction, so derived-data changes
    (stale flags, queued jobs) commit or roll back together with the change that
    caused them. There is no external broker: durable follow-up work goes through
    the transactional outbox.
    """

    def __init__(self) -> None:
        self._handlers: dict[type, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Handler) -> None:
        """Register a handler for an event type.

        Args:
            event_type: Event class to listen for.
            handler: Async callable receiving the event.
        """
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        """Run every handler subscribed to the event's type, in registration order.

        Args:
            event: Event to deliver.
        """
        for handler in self._handlers[type(event)]:
            await handler(event)


def build_event_bus(session: AsyncSession) -> EventBus:
    """Create the bus with the production handlers bound to ``session``.

    Args:
        session: Session whose transaction the handlers participate in.

    Returns:
        A bus with transcript handlers registered.
    """
    from app.services.processing.handlers import TranscriptEventHandlers
    from app.services.processing.jobs import JobService

    handlers = TranscriptEventHandlers(session, JobService(session))
    bus = EventBus()
    bus.subscribe(TranscriptEdited, handlers.on_edited)
    bus.subscribe(TranscriptReplaced, handlers.on_replaced)
    return bus
