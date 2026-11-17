from typing import Literal

import anyio.to_thread
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.auth import require_service_token
from app.deps import Embedder

router = APIRouter(tags=["Embeddings"], dependencies=[Depends(require_service_token)])

MAX_TEXTS = 256
MAX_TEXT_LENGTH = 4000


class EmbeddingsRequest(BaseModel):
    """Texts to embed. E5 models need different prefixes for stored passages and queries."""

    texts: list[str] = Field(min_length=1, max_length=MAX_TEXTS)
    kind: Literal["passage", "query"] = "passage"


class EmbeddingsResponse(BaseModel):
    """One normalized vector per input text."""

    vectors: list[list[float]]
    model: str
    dimensions: int


@router.post("/embeddings", response_model=EmbeddingsResponse)
async def create_embeddings(payload: EmbeddingsRequest, embedder: Embedder) -> EmbeddingsResponse:
    """Embed texts with the process-wide model, off the event loop."""
    texts = [f"{payload.kind}: {text[:MAX_TEXT_LENGTH]}" for text in payload.texts]
    vectors = await anyio.to_thread.run_sync(embedder.encode, texts)
    return EmbeddingsResponse(
        vectors=vectors,
        model=getattr(embedder, "model_name", "unknown"),
        dimensions=len(vectors[0]) if vectors else 0,
    )
