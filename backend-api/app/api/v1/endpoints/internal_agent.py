from fastapi import APIRouter, Query, status

from app.api.deps import (
    AccessPolicy,
    AgentActionServiceDep,
    AgentToolServiceDep,
    ArtifactServiceDep,
    QuotaServiceDep,
)
from app.api.internal_deps import ScopedAgent
from app.domain.enums import Permission
from app.schemas.agent import (
    AgentActionResponse,
    AgentSegment,
    AgentSummaryResponse,
    ArtifactCreateRequest,
    ArtifactResponse,
    FindRequest,
    OverviewResponse,
    ProposalRequest,
    SearchHit,
    SearchRequest,
)

router = APIRouter(prefix="/internal/agent/v1", tags=["Agent tools (internal)"])


@router.get("/meetings/{meeting_id}/overview", response_model=OverviewResponse)
async def get_meeting_overview(ctx: ScopedAgent, tools: AgentToolServiceDep) -> OverviewResponse:
    """Title, state, revision and per-speaker talk time."""
    return await tools.overview(ctx.actor, ctx.meeting_id)


@router.post("/meetings/{meeting_id}/search", response_model=list[SearchHit])
async def search_transcript(
    payload: SearchRequest, ctx: ScopedAgent, tools: AgentToolServiceDep
) -> list[SearchHit]:
    """Hybrid retrieval over the indexed transcript."""
    return await tools.search(ctx.actor, ctx.meeting_id, payload.query, payload.k)


@router.get("/meetings/{meeting_id}/segments", response_model=list[AgentSegment])
async def read_segments(
    ctx: ScopedAgent,
    tools: AgentToolServiceDep,
    from_time: float | None = Query(default=None, ge=0),
    to_time: float | None = Query(default=None, ge=0),
    speaker: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AgentSegment]:
    """Segments in a time window and/or of one speaker."""
    return await tools.read_segments(ctx.actor, ctx.meeting_id, from_time, to_time, speaker, limit)


@router.post("/meetings/{meeting_id}/find", response_model=list[AgentSegment])
async def find_text(
    payload: FindRequest, ctx: ScopedAgent, tools: AgentToolServiceDep
) -> list[AgentSegment]:
    """Segments containing a literal text, with their ids."""
    return await tools.find_text(ctx.actor, ctx.meeting_id, payload.pattern, payload.case_sensitive)


@router.get("/meetings/{meeting_id}/summary", response_model=AgentSummaryResponse)
async def get_summary(ctx: ScopedAgent, tools: AgentToolServiceDep) -> AgentSummaryResponse:
    """Summary, key points and action items."""
    return await tools.get_summary(ctx.actor, ctx.meeting_id)


@router.post(
    "/meetings/{meeting_id}/agent-actions",
    response_model=AgentActionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def propose_action(
    payload: ProposalRequest, ctx: ScopedAgent, actions: AgentActionServiceDep
) -> AgentActionResponse:
    """Store a proposed change (transcript edit, action items, summary regeneration).

    Nothing is written to the meeting: the user must approve the proposal first.
    """
    action = await actions.propose(ctx.actor, ctx.conversation_id, ctx.meeting_id, payload)
    return AgentActionResponse.model_validate(action)


@router.post(
    "/meetings/{meeting_id}/artifacts",
    response_model=ArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_artifact(
    payload: ArtifactCreateRequest,
    ctx: ScopedAgent,
    artifacts: ArtifactServiceDep,
    policy: AccessPolicy,
    quota: QuotaServiceDep,
) -> ArtifactResponse:
    """Generate a document (minutes, email draft, subtitles). Non-destructive, so no approval."""
    meeting = await policy.require(ctx.actor, ctx.meeting_id, Permission.VIEW)
    await quota.assert_agent_allowed(ctx.user.id)
    artifact = await artifacts.create(
        meeting, ctx.user.id, payload.kind, payload.title, payload.content_markdown
    )
    return ArtifactResponse.model_validate(artifact)

