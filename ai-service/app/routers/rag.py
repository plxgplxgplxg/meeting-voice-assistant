from typing import Any

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.auth import require_service_token
from app.deps import AnswerGeneratorDep, RetrieverDep, SummaryGeneratorDep

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/rag", tags=["RAG QA"], dependencies=[Depends(require_service_token)]
)


class CitationItem(BaseModel):
    """Citation metadata linking an assertion directly to an audio segment."""
    segment_id: str = Field(description="Unique UUID or ID of the segment")
    speaker_label: str = Field(description="Label or name of the speaker")
    start_time: float = Field(description="Start time in seconds")
    end_time: float = Field(description="End time in seconds")
    quote: str = Field(description="Direct text quote from the meeting")


class RAGQueryRequest(BaseModel):
    """Payload to query meeting knowledge base with conversation history and candidate segments."""
    meeting_id: str
    query: str
    segments: list[dict[str, Any]] = Field(default_factory=list)
    chat_history: list[dict[str, str]] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=20)


class RAGQueryResponse(BaseModel):
    """RAG response containing answer and verified audio citations."""
    answer: str
    citations: list[CitationItem] = Field(default_factory=list)


class SummarizeRequest(BaseModel):
    """Payload requesting executive summary and action items."""
    meeting_id: str
    full_transcript: str


class SummarizeResponse(BaseModel):
    """Structured meeting summary output."""
    executive_summary: str
    key_points: list[str] = Field(default_factory=list)
    action_items: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/query", response_model=RAGQueryResponse)
async def query_meeting(
    payload: RAGQueryRequest,
    retriever: RetrieverDep,
    generator: AnswerGeneratorDep,
) -> RAGQueryResponse:
    """Query meeting knowledge base using Hybrid Search (e5-small + Lexical RRF) and Gemini 2.0 Flash."""
    logger.info("rag_query_received", meeting_id=payload.meeting_id, query=payload.query, seg_count=len(payload.segments))

    # 1. Retrieve most relevant context segments
    matched_segments = await retriever.retrieve(
        query=payload.query,
        segments=payload.segments,
        top_k=payload.top_k,
    )

    # 2. Generate answer with verifiable citations via Gemini 2.0 Flash / OpenAI
    result = await generator.answer_query(
        query=payload.query,
        context_segments=matched_segments,
        chat_history=payload.chat_history,
    )

    formatted_citations = [
        CitationItem(
            segment_id=str(c.get("segment_id", "")),
            speaker_label=str(c.get("speaker_label", "Người nói")),
            start_time=float(c.get("start_time", 0.0)),
            end_time=float(c.get("end_time", 0.0)),
            quote=str(c.get("quote", "")),
        )
        for c in result.get("citations", [])
    ]

    return RAGQueryResponse(
        answer=result.get("answer", ""),
        citations=formatted_citations,
    )


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_meeting(
    payload: SummarizeRequest, generator: SummaryGeneratorDep
) -> SummarizeResponse:
    """Generate structured summary and action items using Gemini 2.0 Flash or GPT-4o-mini."""
    logger.info("rag_summarize_received", meeting_id=payload.meeting_id)
    result = await generator.generate_summary(payload.full_transcript)
    return SummarizeResponse(
        executive_summary=result.get("executive_summary", ""),
        key_points=result.get("key_points", []),
        action_items=result.get("action_items", []),
    )
