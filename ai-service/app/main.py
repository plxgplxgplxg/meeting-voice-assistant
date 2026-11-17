from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import anyio.to_thread
import httpx
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import ai_settings
from app.core.errors import ProviderNotConfiguredError, ServiceError
from app.rag.embeddings import EmbeddingModelWrapper
from app.routers import audio, rag

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create process-wide resources once: HTTP client and the embedding model.

    A missing embedding model does not stop the service. It is reported as
    ``degraded`` by ``/health`` and requests that need it fail explicitly.
    """
    app.state.http = httpx.AsyncClient(timeout=60.0)
    app.state.embedder = EmbeddingModelWrapper()
    app.state.embedder_error = None
    if not ai_settings.use_mock_engine:
        try:
            await anyio.to_thread.run_sync(app.state.embedder.load)
        except ProviderNotConfiguredError as exc:
            app.state.embedder_error = exc.message
    yield
    await app.state.http.aclose()


app = FastAPI(
    title=ai_settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if ai_settings.is_production else "/docs",
    redoc_url=None,
    openapi_url=None if ai_settings.is_production else "/openapi.json",
)

app.include_router(audio.router)
app.include_router(rag.router)


@app.exception_handler(ServiceError)
async def handle_service_error(request: Request, exc: ServiceError) -> JSONResponse:
    """Map service errors to the standard error envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "path": request.url.path}},
    )


def collect_degraded_reasons(request: Request) -> list[str]:
    """List why the service cannot fully serve requests, empty when healthy."""
    if ai_settings.use_mock_engine:
        return []
    reasons: list[str] = []
    if not ai_settings.gladia_api_key:
        reasons.append("ASR provider not configured")
    llm_key = (
        ai_settings.gemini_api_key if ai_settings.llm_provider == "gemini" else ai_settings.openai_api_key
    )
    if not llm_key:
        reasons.append("LLM provider not configured")
    embedder_error = getattr(request.app.state, "embedder_error", None)
    if embedder_error:
        reasons.append(embedder_error)
    return reasons


@app.get("/health", tags=["Health"])
async def health_check(request: Request) -> dict[str, object]:
    """Health probe reporting ``degraded`` with reasons when a provider is unavailable."""
    reasons = collect_degraded_reasons(request)
    return {
        "status": "degraded" if reasons else "healthy",
        "service": "ai-service",
        "reasons": reasons,
    }
