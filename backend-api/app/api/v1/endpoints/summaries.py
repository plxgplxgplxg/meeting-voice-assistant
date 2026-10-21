import uuid
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.schemas.summary import ActionItemResponse, SummaryResponse

router = APIRouter(prefix="/summaries", tags=["Summaries"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/{meeting_id}", response_model=SummaryResponse | None)
async def get_meeting_summary(meeting_id: uuid.UUID, db: DatabaseSession) -> SummaryResponse | None:
    """Retrieve the AI generated summary for a meeting."""
    return None


@router.get("/{meeting_id}/action-items", response_model=list[ActionItemResponse])
async def list_action_items(meeting_id: uuid.UUID, db: DatabaseSession) -> list[ActionItemResponse]:
    """Retrieve action items associated with a meeting."""
    return []
