import os
import uuid
import zlib
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
from app.api.deps import (
    get_agent_stream_client,
    get_ai_client,
    get_retriever,
    get_storage_service,
)
from app.clients.ai_service_client import TranscriptionStatus
from app.core.config import settings
from app.core.database import Base, get_db_session
from app.core.errors import AIUnavailableError, ValidationFailedError
from app.main import app as fastapi_app
from app.models.meeting import MeetingModel
from app.services.audio_probe import AudioMetadata
from app.services.billing.plan_service import PlanService
from app.services.retrieval_service import RetrievedChunk
from app.services.storage_service import StorageService


@pytest.fixture(scope="session", autouse=True)
def fast_password_hashing() -> None:
    """Use the minimum bcrypt cost so tests that register accounts stay fast."""
    settings.bcrypt_rounds = 4


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw) -> str:
    """Compile JSONB column type as standard JSON for SQLite."""
    return "JSON"


def hashed_bag_of_words(text: str, dimensions: int = 384) -> list[float]:
    """Deterministic embedding: texts sharing words get similar normalized vectors."""
    vector = [0.0] * dimensions
    for word in text.lower().replace(":", " ").split():
        vector[zlib.crc32(word.encode()) % dimensions] += 1.0
    norm = sum(v * v for v in vector) ** 0.5 or 1.0
    return [v / norm for v in vector]


@dataclass
class FakeAIClient:
    """Scriptable AIServiceClient used by tests."""

    segments: list[dict[str, Any]] = field(default_factory=list)
    is_demo: bool = False
    summary: dict[str, Any] = field(default_factory=dict)
    answer: tuple[str, list[dict[str, Any]]] = ("", [])
    submit_error: AIUnavailableError | None = None
    poll_error: AIUnavailableError | None = None
    transcription_error: str | None = None
    pending_polls: int = 0
    summary_error: AIUnavailableError | None = None
    query_error: AIUnavailableError | None = None
    embed_error: AIUnavailableError | None = None
    provider_job_id: str = "prov-1"
    submissions: list[str] = field(default_factory=list)
    polls: int = 0
    queries: list[dict[str, Any]] = field(default_factory=list)
    embedded: list[tuple[str, list[str]]] = field(default_factory=list)

    async def submit_transcription(
        self, meeting_id: str, storage_key: str, language: str = "vi"
    ) -> str:
        if self.submit_error:
            raise self.submit_error
        self.submissions.append(storage_key)
        return self.provider_job_id

    async def get_transcription(self, provider_job_id: str) -> TranscriptionStatus:
        self.polls += 1
        if self.poll_error:
            raise self.poll_error
        if self.polls <= self.pending_polls:
            return TranscriptionStatus("processing")
        if self.transcription_error:
            return TranscriptionStatus("error", error=self.transcription_error)
        return TranscriptionStatus("done", self.segments, self.is_demo)

    async def summarize(self, meeting_id: str, transcript: str) -> dict[str, Any]:
        if self.summary_error:
            raise self.summary_error
        return self.summary

    async def embed(self, texts: list[str], kind: str) -> list[list[float]]:
        if self.embed_error:
            raise self.embed_error
        self.embedded.append((kind, texts))
        return [hashed_bag_of_words(text) for text in texts]

    async def rag_answer(
        self,
        query: str,
        chunks: list[dict[str, Any]],
        chat_history: list[dict[str, str]],
    ) -> tuple[str, list[dict[str, Any]]]:
        self.queries.append({"query": query, "chunks": chunks})
        if self.query_error:
            raise self.query_error
        return self.answer


@dataclass
class FakeProbe:
    """AudioProbe returning scripted metadata."""

    duration: float = 90.0
    error: ValidationFailedError | None = None
    calls: int = 0

    async def probe(self, path) -> AudioMetadata:
        self.calls += 1
        if self.error:
            raise self.error
        return AudioMetadata(duration_seconds=self.duration, codec="pcm_s16le", container="wav")


@dataclass
class FakeIndexer:
    """TranscriptIndexer recording rebuilds."""

    error: AIUnavailableError | None = None
    rebuilt: list[tuple[uuid.UUID, int]] = field(default_factory=list)

    async def rebuild_index(self, meeting_id: uuid.UUID, revision: int) -> int:
        if self.error:
            raise self.error
        self.rebuilt.append((meeting_id, revision))
        return 1


@dataclass
class FakeRetriever:
    """TranscriptRetriever returning scripted chunks."""

    chunks: list[RetrievedChunk] = field(default_factory=list)
    searches: list[tuple[uuid.UUID, str, int]] = field(default_factory=list)

    async def search(self, meeting_id: uuid.UUID, query: str, k: int = 5) -> list[RetrievedChunk]:
        self.searches.append((meeting_id, query, k))
        return self.chunks[:k]


@dataclass
class FakeAgentClient:
    """AgentStreamClient driven by a script, optionally calling back into the API like the real agent."""

    script: Callable[[dict[str, Any]], AsyncIterator[dict[str, Any]]] | None = None
    payloads: list[dict[str, Any]] = field(default_factory=list)
    error: AIUnavailableError | None = None

    async def stream_turn(self, payload: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        self.payloads.append(payload)
        if self.error:
            raise self.error
        if self.script is None:
            yield {"type": "token", "data": {"text": "ok"}}
            yield {"type": "done", "data": {}}
            return
        async for item in self.script(payload):
            yield item


@dataclass
class RecordingSender:
    """TaskSender recording published tasks."""

    sent: list[tuple[str, list[Any]]] = field(default_factory=list)
    fail: bool = False

    def send(self, task_name: str, args: list[Any]) -> None:
        if self.fail:
            raise ConnectionError("broker down")
        self.sent.append((task_name, args))


@dataclass
class Account:
    """An authenticated test account."""

    id: uuid.UUID
    email: str
    headers: dict[str, str]
    refresh_token: str


TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

# Tables using pgvector, tsvector or array columns cannot be created on SQLite
POSTGRES_ONLY_TABLES = {"transcript_chunks"}


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

        sqlite_tables = [
            table for name, table in Base.metadata.tables.items() if name not in POSTGRES_ONLY_TABLES
        ]
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=sqlite_tables))

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
def fake_probe() -> FakeProbe:
    """Scriptable audio probe."""
    return FakeProbe()


@pytest.fixture
def fake_indexer() -> FakeIndexer:
    """Recording transcript indexer."""
    return FakeIndexer()


@pytest.fixture
def fake_retriever() -> FakeRetriever:
    """Scriptable transcript retriever."""
    return FakeRetriever()


@pytest.fixture
def fake_agent() -> FakeAgentClient:
    """Scriptable assistant stream client."""
    return FakeAgentClient()


@pytest.fixture
def sender() -> RecordingSender:
    """Recording broker publisher."""
    return RecordingSender()


@pytest.fixture
def storage(tmp_path: Path) -> StorageService:
    """Storage rooted in a temporary directory with a small upload limit."""
    return StorageService(root_dir=str(tmp_path / "storage"), max_upload_mb=1)


@pytest_asyncio.fixture(loop_scope="function")
async def client(
    db_session: AsyncSession,
    fake_ai: FakeAIClient,
    fake_retriever: FakeRetriever,
    fake_agent: FakeAgentClient,
    storage: StorageService,
) -> AsyncIterator[AsyncClient]:
    """Create an AsyncClient with the DB session, AI client, storage and dispatcher overridden."""

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    fastapi_app.dependency_overrides[get_db_session] = override_get_db_session
    fastapi_app.dependency_overrides[get_ai_client] = lambda: fake_ai
    fastapi_app.dependency_overrides[get_storage_service] = lambda: storage
    fastapi_app.dependency_overrides[get_retriever] = lambda: fake_retriever
    fastapi_app.dependency_overrides[get_agent_stream_client] = lambda: fake_agent

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
        is_ready = status == "ready"
        meeting = MeetingModel(
            title=title,
            status=status,
            created_by=owner_id,
            share_token=share_token,
            share_permission=share_permission,
            summary_status="ready" if is_ready else "none",
            index_status="ready" if is_ready else "none",
        )
        db_session.add(meeting)
        await db_session.flush()
        return meeting

    return _make


UpgradeToPro = Callable[[uuid.UUID], Awaitable[None]]


@pytest.fixture
def upgrade_to_pro(db_session: AsyncSession) -> UpgradeToPro:
    """Factory moving a user onto the Pro plan, which includes the assistant's tools."""
    from sqlalchemy import select

    from app.core.clock import utc_now
    from app.models.billing import PlanConfigModel
    from app.services.billing.subscription_service import SubscriptionService

    async def _upgrade(user_id: uuid.UUID) -> None:
        pro = await db_session.scalar(select(PlanConfigModel).where(PlanConfigModel.slug == "pro"))
        await SubscriptionService(db_session).activate_paid_plan(user_id, pro, utc_now())

    return _upgrade
