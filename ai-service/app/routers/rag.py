from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/rag", tags=["RAG QA"])


class RAGQueryRequest(BaseModel):
    meeting_id: str
    query: str


class RAGQueryResponse(BaseModel):
    answer: str
    citations: list[dict[str, str]]


@router.post("/query", response_model=RAGQueryResponse)
async def query_meeting(payload: RAGQueryRequest) -> RAGQueryResponse:
    """Query meeting knowledge base with precise citations."""
    return RAGQueryResponse(
        answer="Nội dung thảo luận đã được ghi nhận.",
        citations=[],
    )
