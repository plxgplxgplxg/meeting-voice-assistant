import uuid
from datetime import timedelta
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utc_now
from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationFailedError
from app.domain.actor import Actor
from app.domain.enums import MeetingStatus, Permission
from app.models.agent import AgentActionModel, AgentConversationModel
from app.models.meeting import MeetingModel
from app.models.user import UserModel
from app.schemas.action_item_ops import ActionItemOperation
from app.schemas.agent import ApproveRequest, ProposalRequest
from app.schemas.transcript_ops import TranscriptOperation
from app.services.access_policy import MeetingAccessPolicy
from app.services.billing.quota_service import QuotaService
from app.services.processing.commands import ProcessingCommands
from app.services.summary_service import SummaryService
from app.services.transcript_editor import TranscriptEditor

PROPOSAL_TTL = timedelta(minutes=30)
TRANSCRIPT_OPERATIONS = TypeAdapter(list[TranscriptOperation])
ACTION_ITEM_OPERATIONS = TypeAdapter(list[ActionItemOperation])


class AgentActionService:
    """Stores the assistant's proposals and applies them only after the user approves.

    The model never writes: tools create proposals here, and approval runs the same
    command layer the UI uses, with the approving user's own permissions. Proposals
    expire after 30 minutes or once the transcript moves past their base revision.
    """

    def __init__(
        self,
        session: AsyncSession,
        policy: MeetingAccessPolicy,
        editor: TranscriptEditor,
        summaries: SummaryService,
        commands: ProcessingCommands,
        quota: QuotaService,
    ) -> None:
        """Initialize the service.

        Args:
            session: Active SQLAlchemy session.
            policy: Authorization seam.
            editor: Transcript command layer.
            summaries: Action item operations.
            commands: Summary regeneration.
            quota: Plan gating for agent write tools.
        """
        self.session = session
        self.policy = policy
        self.editor = editor
        self.summaries = summaries
        self.commands = commands
        self.quota = quota

    async def propose(
        self,
        actor: Actor,
        conversation_id: uuid.UUID,
        meeting_id: uuid.UUID,
        request: ProposalRequest,
    ) -> AgentActionModel:
        """Validate a change, compute its preview, and store it as ``proposed``.

        Args:
            actor: The delegated agent identity (acts as the user).
            conversation_id: Conversation the proposal belongs to.
            meeting_id: Meeting the change targets.
            request: The proposed change and the revision it is based on.

        Returns:
            The stored proposal.

        Raises:
            PermissionDeniedError: If the user cannot edit the meeting.
            QuotaExceededError: If the user's plan excludes agent tools.
            ConflictError: If the transcript moved past ``base_revision``.
            ValidationFailedError: If the operations are missing or invalid.
        """
        meeting = await self.policy.require(actor, meeting_id, Permission.EDIT)
        assert actor.user_id is not None
        await self.quota.assert_agent_allowed(actor.user_id)

        payload: dict[str, Any]
        if request.kind == "transcript_ops":
            if not request.operations:
                raise ValidationFailedError("operations are required.", code="VALIDATION_FAILED")
            if meeting.transcript_revision != request.base_revision:
                raise ConflictError(
                    f"The transcript is now at revision {meeting.transcript_revision}.",
                    code="TRANSCRIPT_REVISION_CONFLICT",
                )
            diff = await self.editor.preview(actor, meeting_id, request.operations)
            payload = {"operations": [op.model_dump(mode="json") for op in request.operations]}
            preview = diff.to_response().model_dump(mode="json")
        elif request.kind == "action_item_ops":
            if not request.action_item_operations:
                raise ValidationFailedError(
                    "action_item_operations are required.", code="VALIDATION_FAILED"
                )
            changes = await self.summaries.preview_action_item_operations(
                meeting_id, request.action_item_operations
            )
            payload = {
                "action_item_operations": [
                    op.model_dump(mode="json") for op in request.action_item_operations
                ]
            }
            preview = {"changes": changes}
        else:
            if meeting.status != MeetingStatus.READY:
                raise ConflictError(
                    "The meeting must finish processing first.", code="INVALID_MEETING_STATE"
                )
            payload, preview = {}, {"summary_status_after": "pending"}

        action = AgentActionModel(
            conversation_id=conversation_id,
            meeting_id=meeting_id,
            user_id=actor.user_id,
            kind=request.kind,
            payload=payload,
            preview=preview,
            base_revision=meeting.transcript_revision,
            status="proposed",
        )
        self.session.add(action)
        await self.session.flush()
        return action

    async def approve(
        self,
        user: UserModel,
        meeting_id: uuid.UUID,
        action_id: uuid.UUID,
        edits: ApproveRequest | None = None,
    ) -> AgentActionModel:
        """Apply a proposal on behalf of the user who owns it.

        The change runs through ``TranscriptEditor`` (or the matching command) with
        ``actor_type=agent`` in the history and the revision the proposal was based on,
        so a stale proposal fails with a conflict instead of overwriting newer edits.

        Args:
            user: Approving user; must own the proposal.
            meeting_id: Meeting of the proposal.
            action_id: Proposal to apply.
            edits: Optional edited operations replacing the proposed ones.

        Returns:
            The proposal with status ``applied`` and its result.

        Raises:
            PermissionDeniedError: If the user cannot edit the meeting or does not own the proposal.
            ConflictError: If the proposal was already decided, expired, or is stale.
        """
        meeting = await self.policy.require(Actor(user_id=user.id), meeting_id, Permission.EDIT)
        action = await self._load_owned(user, meeting_id, action_id)
        if action.status != "proposed":
            raise ConflictError("This proposal was already decided.", code="ALREADY_DECIDED")
        await self._reject_if_outdated(action, meeting)

        agent_actor = Actor(user_id=user.id, via="agent")
        result: dict[str, Any]
        if action.kind == "transcript_ops":
            operations = (
                edits.operations
                if edits and edits.operations
                else TRANSCRIPT_OPERATIONS.validate_python(action.payload["operations"])
            )
            applied = await self.editor.apply(
                agent_actor,
                meeting_id,
                operations,
                expected_revision=action.base_revision,
                reason="approved assistant proposal",
                agent_run_id=action.conversation_id,
            )
            action.change_set_id = applied.change_set_id
            result = {
                "revision": applied.revision,
                "affected_segment_ids": [str(i) for i in applied.affected_segment_ids],
            }
        elif action.kind == "action_item_ops":
            item_operations = (
                edits.action_item_operations
                if edits and edits.action_item_operations
                else ACTION_ITEM_OPERATIONS.validate_python(
                    action.payload["action_item_operations"]
                )
            )
            result = {
                "changes": await self.summaries.apply_action_item_operations(
                    meeting_id, item_operations
                )
            }
        else:
            await self.commands.request_summary_regeneration(meeting)
            result = {"summary_status": meeting.summary_status}

        action.status = "applied"
        action.result = result
        action.decided_at = utc_now()
        await self.session.flush()
        return action

    async def reject(
        self, user: UserModel, meeting_id: uuid.UUID, action_id: uuid.UUID
    ) -> AgentActionModel:
        """Discard a proposal without applying it.

        Raises:
            PermissionDeniedError: If the user does not own the proposal or cannot view the meeting.
            ConflictError: If it was already decided.
        """
        await self.policy.require(Actor(user_id=user.id), meeting_id, Permission.VIEW)
        action = await self._load_owned(user, meeting_id, action_id)
        if action.status != "proposed":
            raise ConflictError("This proposal was already decided.", code="ALREADY_DECIDED")
        action.status = "rejected"
        action.decided_at = utc_now()
        await self.session.flush()
        return action

    async def list_for_user(
        self, user: UserModel, meeting_id: uuid.UUID, status: str | None = None
    ) -> list[AgentActionModel]:
        """List the user's own proposals for a meeting, newest first."""
        await self.policy.require(Actor(user_id=user.id), meeting_id, Permission.VIEW)
        query = select(AgentActionModel).where(
            AgentActionModel.meeting_id == meeting_id, AgentActionModel.user_id == user.id
        )
        if status:
            query = query.where(AgentActionModel.status == status)
        result = await self.session.scalars(query.order_by(AgentActionModel.created_at.desc()))
        return list(result.all())

    async def get_in_conversation(
        self, action_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> AgentActionModel | None:
        """Return a proposal only if it belongs to the given conversation."""
        return await self.session.scalar(
            select(AgentActionModel).where(
                AgentActionModel.id == action_id,
                AgentActionModel.conversation_id == conversation_id,
            )
        )

    async def _load_owned(
        self, user: UserModel, meeting_id: uuid.UUID, action_id: uuid.UUID
    ) -> AgentActionModel:
        action = await self.session.scalar(
            select(AgentActionModel).where(
                AgentActionModel.id == action_id, AgentActionModel.meeting_id == meeting_id
            )
        )
        if action is None:
            raise NotFoundError("Proposal not found.", code="PROPOSAL_NOT_FOUND")
        if action.user_id != user.id:
            raise PermissionDeniedError(
                "Only the user the assistant worked for can decide this proposal.",
                code="PROPOSAL_FORBIDDEN",
            )
        return action

    async def _reject_if_outdated(self, action: AgentActionModel, meeting: MeetingModel) -> None:
        """Mark the proposal expired and fail the request when it is too old or stale."""
        too_old = utc_now() - action.created_at > PROPOSAL_TTL
        stale = (
            action.kind == "transcript_ops" and meeting.transcript_revision != action.base_revision
        )
        if not (too_old or stale):
            return
        action.status = "expired"
        action.decided_at = utc_now()
        await self.session.flush()
        raise ConflictError(
            "The proposal expired or the transcript changed since it was made. Ask again.",
            code="PROPOSAL_STALE" if stale else "PROPOSAL_EXPIRED",
            commit_changes=True,
        )


async def conversation_owned_by(
    session: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID, meeting_id: uuid.UUID
) -> AgentConversationModel | None:
    """Return the conversation only when it belongs to this user and meeting."""
    return await session.scalar(
        select(AgentConversationModel).where(
            AgentConversationModel.id == conversation_id,
            AgentConversationModel.user_id == user_id,
            AgentConversationModel.meeting_id == meeting_id,
        )
    )
