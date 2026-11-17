import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TypedDict

import httpx
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

import app.models  # noqa: F401
from app.api.error_handlers import register_exception_handlers
from app.api.v1.endpoints import internal_agent
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import async_session_factory
from app.core.logging import configure_logging
from app.services.billing.plan_service import PlanService

configure_logging(json_logs=settings.is_production)
logger = structlog.get_logger(__name__)


class AppState(TypedDict):
    """Explicit typing for lifespan state resources."""
    http_client: httpx.AsyncClient


async def init_database() -> None:
    """Seed default plans. The schema itself is owned by Alembic migrations.

    Run ``alembic upgrade head`` before starting the application.

    Raises:
        Exception: Re-raises seeding failures in production so the container
            cannot report a false healthy state.
    """
    try:
        async with async_session_factory() as session:
            await PlanService(session).seed_default_plans()
            await session.commit()
        logger.info("database_initialization_success")
    except Exception as exc:
        logger.warning("database_initialization_notice", error=str(exc))
        if settings.is_production:
            raise


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[AppState]:
    """Manage application startup and shutdown lifespan."""
    await init_database()
    http_client = httpx.AsyncClient(timeout=30.0)
    yield {"http_client": http_client}
    await http_client.aclose()


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware attaching a unique X-Request-ID to the request state and response."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        response.headers["X-Request-ID"] = request_id
        return response


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router)
app.include_router(internal_agent.router, include_in_schema=False)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Service health check probe."""
    return {"status": "healthy", "service": "backend-api"}
