from typing import Any

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.auth import require_service_token
from app.deps import AnswerGeneratorDep, SummaryGeneratorDep

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["RAG QA"], dependencies=[Depends(require_service_token)])


class CitationItem(BaseModel):
    """Citation metadata linking an assertion directly to an audio segment."""

    segment_id: str = Field(description="Unique UUID or ID of the segment")
    speaker_label: str = Field(description="Label or name of the speaker")
    start_time: float = Field(description="Start time in seconds")
    end_time: float = Field(description="End time in seconds")
    quote: str = Field(description="Direct text quote from the meeting")


class RAGAnswerRequest(BaseModel):
    """Question plus the chunks the backend already retrieved for it."""

    query: str = Field(min_length=1)
    chunks: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    chat_history: list[dict[str, str]] = Field(default_factory=list, max_length=20)


class RAGAnswerResponse(BaseModel):
    """Answer with verified citations."""

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


@router.post("/rag/answer", response_model=RAGAnswerResponse)
async def answer_question(
    payload: RAGAnswerRequest, generator: AnswerGeneratorDep
) -> RAGAnswerResponse:
    """Answer a question from the supplied chunks, citing them as [S01], [S02], ..."""
    logger.info("rag_answer_received", chunk_count=len(payload.chunks))
    result = await generator.answer_query(
        query=payload.query,
        context_segments=payload.chunks,
        chat_history=payload.chat_history,
    )
    return RAGAnswerResponse(
        answer=result.get("answer", ""),
        citations=[
            CitationItem(
                segment_id=str(c.get("segment_id", "")),
                speaker_label=str(c.get("speaker_label", "Người nói")),
                start_time=float(c.get("start_time", 0.0)),
                end_time=float(c.get("end_time", 0.0)),
                quote=str(c.get("quote", "")),
            )
            for c in result.get("citations", [])
        ],
    )


@router.post("/llm/summarize", response_model=SummarizeResponse)
async def summarize_meeting(
    payload: SummarizeRequest, generator: SummaryGeneratorDep
) -> SummarizeResponse:
    """Generate a structured summary and action items from a full transcript."""
    logger.info("llm_summarize_received", meeting_id=payload.meeting_id)
    result = await generator.generate_summary(payload.full_transcript)
    return SummarizeResponse(
        executive_summary=result.get("executive_summary", ""),
        key_points=result.get("key_points", []),
        action_items=result.get("action_items", []),
    )
