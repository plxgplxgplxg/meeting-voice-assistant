from collections.abc import AsyncIterator
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.compiler import compiles

import app.models  # noqa: F401
from app.core.database import Base, get_db_session
from app.main import app as fastapi_app
from app.services.plan_service import PlanService


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw) -> str:
    """Compile JSONB column type as standard JSON for SQLite."""
    return "JSON"


@pytest_asyncio.fixture(loop_scope="function")
async def test_engine() -> AsyncIterator[AsyncEngine]:
    """Create in-memory SQLite async engine for tests.

    Yields:
        AsyncEngine: Configured test engine.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="function")
async def db_session(test_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Yield test database session with rollback/cleanup.

    Args:
        test_engine: Function-scoped async engine.

    Yields:
        AsyncSession: Active test session.
    """
    session_factory = async_sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        # Seed default plans if empty
        plan_service = PlanService(session)
        await plan_service.seed_default_plans_if_empty()
        await session.commit()

        yield session


@pytest_asyncio.fixture(loop_scope="function")
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Create an AsyncClient with overridden db session dependency.

    Args:
        db_session: Test async session fixture.

    Yields:
        AsyncClient: HTTP test client.
    """
    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    fastapi_app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app),
        base_url="http://test",
    ) as async_client:
        yield async_client

    fastapi_app.dependency_overrides.clear()
