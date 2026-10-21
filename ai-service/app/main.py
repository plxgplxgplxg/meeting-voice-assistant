from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import ai_settings
from app.routers import audio, rag


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage AI models initialization and resource cleanup."""
    yield


app = FastAPI(
    title=ai_settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audio.router)
app.include_router(rag.router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Health probe for AI service."""
    return {"status": "healthy", "service": "ai-service"}
