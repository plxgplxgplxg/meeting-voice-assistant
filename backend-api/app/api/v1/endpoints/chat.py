from fastapi import APIRouter

from app.api.deps import ActorDep, ChatServiceDep, MeetingForView
from app.schemas.chat import ChatMessageResponse, ChatQueryRequest

router = APIRouter(tags=["Chat"])
legacy_router = APIRouter(prefix="/chat", tags=["Chat (deprecated paths)"], deprecated=True)


@router.get("/meetings/{meeting_id}/chat/messages", response_model=list[ChatMessageResponse])
@legacy_router.get("/{meeting_id}/messages", response_model=list[ChatMessageResponse])
async def list_chat_messages(
    meeting: MeetingForView, actor: ActorDep, service: ChatServiceDep
) -> list[ChatMessageResponse]:
    """Retrieve the caller's chat history for a meeting in chronological order."""
    messages = await service.list_messages(meeting.id, actor.user_id)
    return [ChatMessageResponse.model_validate(m) for m in messages]


@router.post("/meetings/{meeting_id}/chat", response_model=ChatMessageResponse)
@legacy_router.post("/{meeting_id}", response_model=ChatMessageResponse)
async def ask_question(
    payload: ChatQueryRequest,
    meeting: MeetingForView,
    actor: ActorDep,
    service: ChatServiceDep,
) -> ChatMessageResponse:
    """Ask a question about a meeting and receive an answer with citations."""
    assistant_msg = await service.ask_question(meeting, actor.user_id, payload.query)
    return ChatMessageResponse.model_validate(assistant_msg)
