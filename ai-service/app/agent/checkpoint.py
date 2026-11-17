from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

CHECKPOINT_SCHEMA = "langgraph"


@asynccontextmanager
async def open_checkpointer(db_url: str) -> AsyncIterator[BaseCheckpointSaver]:
    """Open the conversation-state store.

    With a database URL, state lives in the ``langgraph`` schema of that database through
    ``AsyncPostgresSaver``. This is the ai-service's private state (message history keyed
    by thread id), never business data, which stays in the backend. Without a URL the
    state is kept in memory, which is lost on restart and fine for development.

    Args:
        db_url: PostgreSQL connection string in libpq form (``postgresql://...``), or empty.

    Yields:
        A checkpointer ready for ``graph.compile(checkpointer=...)``.
    """
    if not db_url:
        yield InMemorySaver()
        return

    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg_pool import AsyncConnectionPool

    async with AsyncConnectionPool(
        conninfo=db_url,
        max_size=5,
        open=False,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "options": f"-c search_path={CHECKPOINT_SCHEMA},public",
        },
    ) as pool:
        await pool.open()
        async with pool.connection() as connection:
            await connection.execute(f"CREATE SCHEMA IF NOT EXISTS {CHECKPOINT_SCHEMA}")
        saver = AsyncPostgresSaver(pool)  # type: ignore[arg-type]
        await saver.setup()
        yield saver
