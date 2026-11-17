import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Query, Response, status
from fastapi.responses import StreamingResponse

from app.api.deps import (
    AgentActionServiceDep,
    ArtifactServiceDep,
    AssistantServiceDep,
    CurrentUser,
    MeetingForManage,
    MeetingForView,
    OptionalUser,
    QuotaServiceDep,
)
from app.schemas.agent import (
    AgentActionResponse,
    ApproveRequest,
    ArtifactCreateRequest,
    ArtifactResponse,
    TurnRequest,
)

router = APIRouter(tags=["Assistant"])

SSE_HEADERS = {"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}


def attachment_header(display_name: str, extension: str) -> str:
    """Build a Content-Disposition value that survives non-ASCII titles (RFC 5987).

    Args:
        display_name: Human-readable file name, possibly with Vietnamese characters.
        extension: File extension used for the ASCII fallback name.

    Returns:
        Header value with an ASCII ``filename`` and a UTF-8 ``filename*``.
    """
    return f"attachment; filename=\"artifact.{extension}\"; filename*=UTF-8''{quote(display_name)}"


@router.post("/meetings/{meeting_id}/assistant/turns")
async def start_turn(
    payload: TurnRequest,
    meeting: MeetingForView,
    user: OptionalUser,
    service: AssistantServiceDep,
) -> StreamingResponse:
    """Ask the meeting assistant something and stream the answer as Server-Sent Events.

    Plans with agent tools get the tool-using assistant (writes become proposals the
    user approves). Free plans and share-link guests get cited Q&A. Events: ``token``,
    ``tool_start``, ``tool_end``, ``proposal``, ``citation``, ``done``, ``error``.
    """
    prepared = await service.prepare_turn(user, meeting, payload.message)
    return StreamingResponse(
        service.run_turn(prepared, meeting, user),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.get("/meetings/{meeting_id}/agent-actions", response_model=list[AgentActionResponse])
async def list_agent_actions(
    user: CurrentUser,
    meeting: MeetingForView,
    actions: AgentActionServiceDep,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> list[AgentActionResponse]:
    """List the caller's own assistant proposals for a meeting."""
    items = await actions.list_for_user(user, meeting.id, status_filter)
    return [AgentActionResponse.model_validate(a) for a in items]


@router.post(
    "/meetings/{meeting_id}/agent-actions/{action_id}:approve",
    response_model=AgentActionResponse,
)
async def approve_agent_action(
    action_id: uuid.UUID,
    user: CurrentUser,
    meeting: MeetingForView,
    actions: AgentActionServiceDep,
    payload: ApproveRequest | None = None,
) -> AgentActionResponse:
    """Apply a proposal, optionally with edited operations.

    Fails with 409 when the proposal expired or the transcript changed since it was made.
    """
    action = await actions.approve(user, meeting.id, action_id, payload)
    return AgentActionResponse.model_validate(action)


@router.post(
    "/meetings/{meeting_id}/agent-actions/{action_id}:reject",
    response_model=AgentActionResponse,
)
async def reject_agent_action(
    action_id: uuid.UUID, user: CurrentUser, meeting: MeetingForView, actions: AgentActionServiceDep
) -> AgentActionResponse:
    """Discard a proposal."""
    action = await actions.reject(user, meeting.id, action_id)
    return AgentActionResponse.model_validate(action)


@router.get("/meetings/{meeting_id}/artifacts", response_model=list[ArtifactResponse])
async def list_artifacts(
    meeting: MeetingForView, artifacts: ArtifactServiceDep
) -> list[ArtifactResponse]:
    """List generated documents of a meeting."""
    return [ArtifactResponse.model_validate(a) for a in await artifacts.list(meeting.id)]


@router.post(
    "/meetings/{meeting_id}/artifacts",
    response_model=ArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_artifact(
    payload: ArtifactCreateRequest,
    user: CurrentUser,
    meeting: MeetingForView,
    artifacts: ArtifactServiceDep,
    quota: QuotaServiceDep,
) -> ArtifactResponse:
    """Generate a document from the meeting (requires a plan with assistant tools)."""
    await quota.assert_agent_allowed(user.id)
    artifact = await artifacts.create(
        meeting, user.id, payload.kind, payload.title, payload.content_markdown
    )
    return ArtifactResponse.model_validate(artifact)


@router.get("/meetings/{meeting_id}/artifacts/{artifact_id}/download")
async def download_artifact(
    artifact_id: uuid.UUID, meeting: MeetingForView, artifacts: ArtifactServiceDep
) -> Response:
    """Download a generated document."""
    artifact = await artifacts.get(meeting.id, artifact_id)
    data = artifacts.storage.resolve(artifact.storage_key).read_bytes()
    extension = artifact.storage_key.rsplit(".", 1)[-1]
    display_name = f"{artifact.title[:60].replace('/', '_')}.{extension}"
    return Response(
        content=data,
        media_type=artifact.mime_type,
        headers={"Content-Disposition": attachment_header(display_name, extension)},
    )


@router.delete(
    "/meetings/{meeting_id}/artifacts/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_artifact(
    artifact_id: uuid.UUID, meeting: MeetingForManage, artifacts: ArtifactServiceDep
) -> None:
    """Delete a generated document (requires MANAGE on the meeting)."""
    artifact = await artifacts.get(meeting.id, artifact_id)
    await artifacts.delete(artifact)

