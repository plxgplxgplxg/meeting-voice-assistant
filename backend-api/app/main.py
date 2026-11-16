import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TypedDict
import httpx
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from sqlalchemy import text
import structlog

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, async_session_factory, engine
import app.models  # noqa: F401
from app.services.plan_service import PlanService

logger = structlog.get_logger(__name__)


class DomainError(Exception):
    """Base domain exception with error code and status mapping."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AppState(TypedDict):
    """Explicit typing for lifespan state resources."""
    http_client: httpx.AsyncClient


async def init_database() -> None:
    """Initialize database extensions, schema tables, and seed initial plans."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            await conn.run_sync(Base.metadata.create_all)

        async with async_session_factory() as session:
            plan_service = PlanService(session)
            await plan_service.seed_default_plans_if_empty()
            await session.commit()
        logger.info("database_initialization_success")
    except Exception as exc:
        logger.warning("database_initialization_notice", error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[AppState]:
    """Manage application startup and shutdown lifespan."""
    await init_database()
    http_client = httpx.AsyncClient(timeout=30.0)
    yield {"http_client": http_client}
    await http_client.aclose()


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware attaching unique X-Request-ID to request and response."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Handle domain errors formatted as RFC 7807."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "path": request.url.path,
            }
        },
    )


app.include_router(api_router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Service health check probe."""
    return {"status": "healthy", "service": "backend-api"}
