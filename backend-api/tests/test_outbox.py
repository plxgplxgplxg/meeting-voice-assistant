import pytest
from sqlalchemy import select

from app.models.outbox import OutboxEventModel
from app.services.processing.outbox import OutboxRelay, OutboxService
from tests.conftest import RecordingSender


@pytest.mark.asyncio
async def test_relay_publishes_pending_events_once_and_in_order(db_session, sender) -> None:
    outbox = OutboxService(db_session)
    await outbox.enqueue("task_a", ["1"])
    await outbox.enqueue("task_b", ["2"])

    relay = OutboxRelay(db_session, sender)
    assert await relay.dispatch_pending() == 2
    assert await relay.dispatch_pending() == 0

    assert sender.sent == [("task_a", ["1"]), ("task_b", ["2"])]
    rows = (await db_session.scalars(select(OutboxEventModel))).all()
    assert all(row.dispatched_at is not None and row.attempts == 1 for row in rows)


@pytest.mark.asyncio
async def test_broker_outage_leaves_events_pending_until_it_recovers(db_session) -> None:
    """A Redis outage never loses work: rows stay pending and go out on a later poll."""
    await OutboxService(db_session).enqueue("task_a", [])
    down = RecordingSender(fail=True)

    assert await OutboxRelay(db_session, down).dispatch_pending() == 0
    pending = (await db_session.scalars(select(OutboxEventModel))).one()
    assert pending.dispatched_at is None

    recovered = RecordingSender()
    assert await OutboxRelay(db_session, recovered).dispatch_pending() == 1
    assert recovered.sent == [("task_a", [])]
