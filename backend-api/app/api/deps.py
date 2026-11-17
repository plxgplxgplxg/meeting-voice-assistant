import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated

import structlog
from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.ai_service_client import (
    AgentStreamClient,
    AIServiceClient,
    HttpAgentStreamClient,
    HttpAIServiceClient,
)
from app.core.config import settings
from app.core.database import get_db_session
from app.core.errors import AuthenticationError, PermissionDeniedError
from app.core.security import decode_jwt_token
from app.domain.actor import Actor
from app.domain.enums import Permission
from app.models.meeting import MeetingModel
from app.models.user import UserModel
from app.services.access_policy import MeetingAccessPolicy
from app.services.agent_actions import AgentActionService
from app.services.agent_tools import AgentToolService
from app.services.artifact_service import ArtifactService
from app.services.assistant_service import AssistantService
from app.services.audio_service import AudioService
from app.services.billing.plan_service import PlanService
from app.services.billing.quota_service import QuotaService
from app.services.chat_service import ChatService
from app.services.event_bus import EventBus, build_event_bus
from app.services.export.service import ExportService
from app.services.meeting_service import MeetingService
from app.services.processing.commands import ProcessingCommands
from app.services.processing.jobs import JobService
from app.services.retrieval_service import RetrievalService, TranscriptRetriever
from app.services.storage_service import StorageService
from app.services.summary_service import SummaryService
from app.services.transcript_editor import TranscriptEditor
from app.services.transcript_service import TranscriptService

http_bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)]


async def _load_user_from_token(token: str, db: AsyncSession) -> UserModel:
    """Resolve and validate the user referenced by an access token.

    Args:
        token: Encoded JWT access token.
        db: Active database session.

    Returns:
        The active user the token belongs to.

    Raises:
        AuthenticationError: If the token is invalid, wrong type, stale, or the user is gone.
        PermissionDeniedError: If the account is deactivated.
    """
    payload = decode_jwt_token(token)
    if payload.get("type") != "access":
        raise AuthenticationError("Invalid or expired token.", code="INVALID_TOKEN")

    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except ValueError as exc:
        raise AuthenticationError("Invalid or expired token.", code="INVALID_TOKEN") from exc

    user = (
        await db.execute(select(UserModel).where(UserModel.id == user_id))
    ).scalar_one_or_none()
    if user is None or payload.get("tv") != user.token_version:
        raise AuthenticationError("Invalid or expired token.", code="INVALID_TOKEN")
    if not user.is_active:
        raise PermissionDeniedError("User account is deactivated.", code="ACCOUNT_DISABLED")
    structlog.contextvars.bind_contextvars(user_id=str(user.id))
    return user


async def get_current_user(auth: BearerCredentials, db: DbSession) -> UserModel:
    """Require an authenticated user.

    Args:
        auth: Parsed Authorization header.
        db: Active database session.

    Returns:
        The authenticated user.

    Raises:
        AuthenticationError: If no valid access token is presented.
    """
    if not auth or not auth.credentials:
        raise AuthenticationError("Authentication required.")
    return await _load_user_from_token(auth.credentials, db)


async def get_current_user_optional(auth: BearerCredentials, db: DbSession) -> UserModel | None:
    """Resolve the user when a valid token is presented, otherwise None.

    Args:
        auth: Parsed Authorization header.
        db: Active database session.

    Returns:
        The authenticated user, or None for anonymous or invalid credentials.
    """
    if not auth or not auth.credentials:
        return None
    try:
        return await _load_user_from_token(auth.credentials, db)
    except (AuthenticationError, PermissionDeniedError):
        return None


CurrentUser = Annotated[UserModel, Depends(get_current_user)]
OptionalUser = Annotated[UserModel | None, Depends(get_current_user_optional)]


async def get_actor(
    user: OptionalUser,
    share: Annotated[str | None, Query(alias="share")] = None,
) -> Actor:
    """Build the acting identity from the bearer token and optional share token.

    Args:
        user: User resolved from the Authorization header, if any.
        share: Share token from the ``share`` query parameter.

    Returns:
        Actor carrying the user id and share token.
    """
    if user is not None:
        return Actor(user_id=user.id, share_token=share, via="user")
    return Actor(user_id=None, share_token=share, via="share")


ActorDep = Annotated[Actor, Depends(get_actor)]


def get_access_policy(db: DbSession) -> MeetingAccessPolicy:
    """Provide the meeting access policy bound to the request session."""
    return MeetingAccessPolicy(db)


AccessPolicy = Annotated[MeetingAccessPolicy, Depends(get_access_policy)]


def meeting_for(permission: Permission) -> Callable[..., Awaitable[MeetingModel]]:
    """Create a dependency that loads the path meeting after an access check.

    Args:
        permission: Minimum permission the caller must hold.

    Returns:
        FastAPI dependency resolving ``meeting_id`` from the path.
    """

    async def dependency(
        meeting_id: uuid.UUID, actor: ActorDep, policy: AccessPolicy
    ) -> MeetingModel:
        return await policy.require(actor, meeting_id, permission)

    return dependency


MeetingForView = Annotated[MeetingModel, Depends(meeting_for(Permission.VIEW))]
MeetingForEdit = Annotated[MeetingModel, Depends(meeting_for(Permission.EDIT))]
MeetingForManage = Annotated[MeetingModel, Depends(meeting_for(Permission.MANAGE))]


def get_ai_client(request: Request) -> AIServiceClient:
    """Provide the AI service client backed by the lifespan HTTP client."""
    return HttpAIServiceClient(
        settings.ai_service_url, settings.ai_service_token, request.state.http_client
    )


def get_storage_service() -> StorageService:
    """Provide the object storage service."""
    return StorageService()


AIClient = Annotated[AIServiceClient, Depends(get_ai_client)]
Storage = Annotated[StorageService, Depends(get_storage_service)]


def get_meeting_service(db: DbSession, policy: AccessPolicy) -> MeetingService:
    """Provide the meeting service."""
    return MeetingService(db, policy)


def get_transcript_service(db: DbSession) -> TranscriptService:
    """Provide the transcript service."""
    return TranscriptService(db)


def get_summary_service(db: DbSession) -> SummaryService:
    """Provide the summary service."""
    return SummaryService(db)


def get_quota_service(db: DbSession) -> QuotaService:
    """Provide the quota service."""
    return QuotaService(db)


def get_plan_service(db: DbSession) -> PlanService:
    """Provide the plan service."""
    return PlanService(db)


def get_job_service(db: DbSession) -> JobService:
    """Provide the processing job service."""
    return JobService(db)


def get_retriever(db: DbSession, ai_client: AIClient) -> TranscriptRetriever:
    """Provide hybrid transcript retrieval."""
    return RetrievalService(db, ai_client)


Retriever = Annotated[TranscriptRetriever, Depends(get_retriever)]


def get_processing_commands(
    db: DbSession, jobs: Annotated[JobService, Depends(get_job_service)]
) -> ProcessingCommands:
    """Provide the user-triggered processing commands."""
    return ProcessingCommands(db, jobs)


def get_chat_service(db: DbSession, ai_client: AIClient, retriever: Retriever) -> ChatService:
    """Provide the chat service."""
    return ChatService(db, ai_client, retriever)


def get_export_service(db: DbSession) -> ExportService:
    """Provide the export service."""
    return ExportService(db)


def get_audio_service(
    db: DbSession,
    storage: Storage,
    quota: Annotated[QuotaService, Depends(get_quota_service)],
    jobs: Annotated[JobService, Depends(get_job_service)],
) -> AudioService:
    """Provide the audio ingestion service."""
    return AudioService(db, storage, quota, jobs)


MeetingServiceDep = Annotated[MeetingService, Depends(get_meeting_service)]
TranscriptServiceDep = Annotated[TranscriptService, Depends(get_transcript_service)]
SummaryServiceDep = Annotated[SummaryService, Depends(get_summary_service)]
QuotaServiceDep = Annotated[QuotaService, Depends(get_quota_service)]
PlanServiceDep = Annotated[PlanService, Depends(get_plan_service)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
ExportServiceDep = Annotated[ExportService, Depends(get_export_service)]
AudioServiceDep = Annotated[AudioService, Depends(get_audio_service)]
ProcessingCommandsDep = Annotated[ProcessingCommands, Depends(get_processing_commands)]


def get_event_bus(db: DbSession) -> EventBus:
    """Provide the in-process event bus bound to the request transaction."""
    return build_event_bus(db)


def get_transcript_editor(
    db: DbSession, policy: AccessPolicy, events: Annotated[EventBus, Depends(get_event_bus)]
) -> TranscriptEditor:
    """Provide the transcript command layer."""
    return TranscriptEditor(db, policy, events)


TranscriptEditorDep = Annotated[TranscriptEditor, Depends(get_transcript_editor)]


def get_agent_stream_client(request: Request) -> AgentStreamClient:
    """Provide the streaming client for assistant turns."""
    return HttpAgentStreamClient(
        settings.ai_service_url, settings.ai_service_token, request.state.http_client
    )


AgentStream = Annotated[AgentStreamClient, Depends(get_agent_stream_client)]


def get_agent_action_service(
    db: DbSession,
    policy: AccessPolicy,
    editor: TranscriptEditorDep,
    summaries: Annotated[SummaryService, Depends(get_summary_service)],
    commands: Annotated[ProcessingCommands, Depends(get_processing_commands)],
    quota: Annotated[QuotaService, Depends(get_quota_service)],
) -> AgentActionService:
    """Provide the proposal service."""
    return AgentActionService(db, policy, editor, summaries, commands, quota)


def get_agent_tool_service(
    db: DbSession,
    policy: AccessPolicy,
    retriever: Retriever,
    summaries: Annotated[SummaryService, Depends(get_summary_service)],
) -> AgentToolService:
    """Provide the assistant's read tools."""
    return AgentToolService(db, policy, retriever, summaries)


def get_artifact_service(db: DbSession, storage: Storage) -> ArtifactService:
    """Provide artifact generation and storage."""
    return ArtifactService(db, storage)


def get_assistant_service(
    db: DbSession,
    chat: Annotated[ChatService, Depends(get_chat_service)],
    agent_client: AgentStream,
    actions: Annotated[AgentActionService, Depends(get_agent_action_service)],
    quota: Annotated[QuotaService, Depends(get_quota_service)],
) -> AssistantService:
    """Provide the assistant turn orchestrator."""
    return AssistantService(db, chat, agent_client, actions, quota)


AgentActionServiceDep = Annotated[AgentActionService, Depends(get_agent_action_service)]
AgentToolServiceDep = Annotated[AgentToolService, Depends(get_agent_tool_service)]
ArtifactServiceDep = Annotated[ArtifactService, Depends(get_artifact_service)]
AssistantServiceDep = Annotated[AssistantService, Depends(get_assistant_service)]
