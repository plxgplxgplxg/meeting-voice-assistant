import os
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401
from app.api.deps import get_ai_client, get_dispatcher, get_storage_service
from app.clients.ai_service_client import AudioTranscription
from app.core.config import settings
from app.core.database import Base, get_db_session
from app.core.errors import AIUnavailableError
from app.main import app as fastapi_app
from app.models.meeting import MeetingModel
from app.services.billing.plan_service import PlanService
from app.services.storage_service import StorageService


@pytest.fixture(scope="session", autouse=True)
def fast_password_hashing() -> None:
    """Use the minimum bcrypt cost so tests that register accounts stay fast."""
    settings.bcrypt_rounds = 4


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw) -> str:
    """Compile JSONB column type as standard JSON for SQLite."""
    return "JSON"


@dataclass
class FakeAIClient:
    """Scriptable AIServiceClient used by tests."""

    segments: list[dict[str, Any]] = field(default_factory=list)
    is_demo: bool = False
    summary: dict[str, Any] = field(default_factory=dict)
    answer: tuple[str, list[dict[str, Any]]] = ("", [])
    audio_error: AIUnavailableError | None = None
    summary_error: AIUnavailableError | None = None
    query_error: AIUnavailableError | None = None
    audio_calls: int = 0
    queries: list[dict[str, Any]] = field(default_factory=list)

    async def transcribe(
        self, meeting_id: str, storage_key: str, language: str = "vi"
    ) -> AudioTranscription:
        self.audio_calls += 1
        if self.audio_error:
            raise self.audio_error
        return AudioTranscription(segments=self.segments, is_demo=self.is_demo)

    async def summarize(self, meeting_id: str, transcript: str) -> dict[str, Any]:
        if self.summary_error:
            raise self.summary_error
        return self.summary

    async def rag_query(
        self,
        meeting_id: str,
        query: str,
        segments: list[dict[str, Any]],
        chat_history: list[dict[str, str]],
    ) -> tuple[str, list[dict[str, Any]]]:
        self.queries.append({"query": query, "segments": segments})
        if self.query_error:
            raise self.query_error
        return self.answer


@dataclass
class RecordingDispatcher:
    """Dispatcher that records calls instead of talking to Celery."""

    calls: list[tuple[uuid.UUID, uuid.UUID]] = field(default_factory=list)

    def dispatch(self, meeting_id: uuid.UUID, audio_file_id: uuid.UUID) -> None:
        self.calls.append((meeting_id, audio_file_id))


@dataclass
class Account:
    """An authenticated test account."""

    id: uuid.UUID
    email: str
    headers: dict[str, str]
    refresh_token: str


TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


@pytest_asyncio.fixture(loop_scope="function")
async def test_engine() -> AsyncIterator[AsyncEngine]:
    """Create the test engine.

    Uses PostgreSQL when ``TEST_DATABASE_URL`` is set (required to exercise row
    locks and real constraints), otherwise an in-memory SQLite database with
    working SAVEPOINT support.
    """
    if TEST_DATABASE_URL:
        engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    else:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        @event.listens_for(engine.sync_engine, "connect")
        def _disable_pysqlite_autobegin(dbapi_connection, _record) -> None:
            dbapi_connection.isolation_level = None

        @event.listens_for(engine.sync_engine, "begin")
        def _emit_begin(conn) -> None:
            conn.exec_driver_sql("BEGIN")

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="function")
async def db_session(test_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Yield a test database session with default plans seeded."""
    session_factory = async_sessionmaker(
        bind=test_engine, autoflush=False, expire_on_commit=False
    )
    async with session_factory() as session:
        await PlanService(session).seed_default_plans()
        await session.commit()
        yield session


@pytest.fixture
def fake_ai() -> FakeAIClient:
    """Scriptable AI client shared by the app and pipeline tests."""
    return FakeAIClient()


@pytest.fixture
def dispatcher() -> RecordingDispatcher:
    """Recording processing dispatcher."""
    return RecordingDispatcher()


@pytest.fixture
def storage(tmp_path: Path) -> StorageService:
    """Storage rooted in a temporary directory with a small upload limit."""
    return StorageService(root_dir=str(tmp_path / "storage"), max_upload_mb=1)


@pytest_asyncio.fixture(loop_scope="function")
async def client(
    db_session: AsyncSession,
    fake_ai: FakeAIClient,
    dispatcher: RecordingDispatcher,
    storage: StorageService,
) -> AsyncIterator[AsyncClient]:
    """Create an AsyncClient with the DB session, AI client, storage and dispatcher overridden."""

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    fastapi_app.dependency_overrides[get_db_session] = override_get_db_session
    fastapi_app.dependency_overrides[get_ai_client] = lambda: fake_ai
    fastapi_app.dependency_overrides[get_storage_service] = lambda: storage
    fastapi_app.dependency_overrides[get_dispatcher] = lambda: dispatcher

    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app), base_url="http://test"
    ) as async_client:
        yield async_client

    fastapi_app.dependency_overrides.clear()


RegisterUser = Callable[[str], Awaitable[Account]]


@pytest.fixture
def register_user(client: AsyncClient) -> RegisterUser:
    """Factory registering an account and returning its credentials."""

    async def _register(email: str) -> Account:
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "full_name": "Test Person", "password": "Password123!"},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        return Account(
            id=uuid.UUID(body["user"]["id"]),
            email=email,
            headers={"Authorization": f"Bearer {body['tokens']['access_token']}"},
            refresh_token=body["tokens"]["refresh_token"],
        )

    return _register


MakeMeeting = Callable[..., Awaitable[MeetingModel]]


@pytest.fixture
def make_meeting(db_session: AsyncSession) -> MakeMeeting:
    """Factory inserting a meeting directly into the database."""

    async def _make(
        owner_id: uuid.UUID | None,
        title: str = "Weekly sync",
        status: str = "ready",
        share_token: str | None = None,
        share_permission: str = "viewer",
    ) -> MeetingModel:
        meeting = MeetingModel(
            title=title,
            status=status,
            created_by=owner_id,
            share_token=share_token,
            share_permission=share_permission,
        )
        db_session.add(meeting)
        await db_session.flush()
        return meeting

    return _make
