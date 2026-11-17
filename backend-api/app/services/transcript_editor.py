import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, ValidationFailedError
from app.domain.actor import Actor
from app.domain.enums import Permission
from app.domain.events import TranscriptEdited
from app.models.meeting import MeetingModel
from app.models.transcript import TranscriptSegmentModel
from app.models.transcript_revision import (
    TranscriptChangeSetModel,
    TranscriptSegmentChangeModel,
)
from app.schemas.transcript_ops import (
    ChangeSetResultResponse,
    SegmentDiffResponse,
    TranscriptDiffResponse,
    TranscriptOperation,
)
from app.services.access_policy import MeetingAccessPolicy
from app.services.event_bus import EventBus
from app.services.transcript_ops import (
    SNAPSHOT_FIELDS,
    PlannedChange,
    SegmentState,
    TranscriptPlanner,
)

REVISION_CONFLICT = "TRANSCRIPT_REVISION_CONFLICT"
REVERT_CONFLICT = "TRANSCRIPT_REVERT_CONFLICT"


@dataclass(frozen=True, slots=True)
class TranscriptDiff:
    """What a set of operations changes (or changed) in the transcript."""

    changes: list[PlannedChange]
    summary: str
    base_revision: int

    def to_response(self) -> TranscriptDiffResponse:
        """Convert to the API representation."""
        return TranscriptDiffResponse(
            changes=[
                SegmentDiffResponse(
                    op=c.kind,
                    segment_id=c.segment_id,
                    before=c.before,
                    after=c.after,
                    order_only=c.order_only,
                )
                for c in self.changes
            ],
            summary=self.summary,
            base_revision=self.base_revision,
        )


@dataclass(frozen=True, slots=True)
class ChangeSetResult:
    """Outcome of applying or reverting operations."""

    change_set_id: uuid.UUID
    revision: int
    affected_segment_ids: list[uuid.UUID]
    diff: TranscriptDiff

    def to_response(self) -> ChangeSetResultResponse:
        """Convert to the API representation."""
        return ChangeSetResultResponse(
            change_set_id=self.change_set_id,
            revision=self.revision,
            affected_segment_ids=self.affected_segment_ids,
            diff=self.diff.to_response(),
        )


def describe(operations: Sequence[TranscriptOperation], changes: Sequence[PlannedChange]) -> str:
    """Short audit summary of a change set.

    Args:
        operations: Logical operations that were applied.
        changes: Resulting segment-level changes.

    Returns:
        Text such as ``replace_text, rename_speaker (5 segments changed)``.
    """
    changed = sum(1 for c in changes if not c.order_only)
    names = ", ".join(dict.fromkeys(op.op for op in operations))
    return f"{names} ({changed} segments changed)"


class TranscriptEditor:
    """Command layer for every transcript mutation.

    REST endpoints, the agent, and background jobs all call these methods, so
    authorization (``MeetingAccessPolicy``), optimistic concurrency, history, and
    domain events are enforced in exactly one place.
    """

    def __init__(
        self, session: AsyncSession, access_policy: MeetingAccessPolicy, events: EventBus
    ) -> None:
        """Initialize the editor.

        Args:
            session: Active SQLAlchemy session; the caller owns the transaction.
            access_policy: Authorization seam.
            events: Bus used to publish ``TranscriptEdited``.
        """
        self.session = session
        self.access_policy = access_policy
        self.events = events

    async def apply(
        self,
        actor: Actor,
        meeting_id: uuid.UUID,
        operations: Sequence[TranscriptOperation],
        expected_revision: int | None,
        reason: str | None = None,
        agent_run_id: uuid.UUID | None = None,
    ) -> ChangeSetResult:
        """Validate and apply operations as one change set.

        Args:
            actor: Identity performing the edit.
            meeting_id: Meeting being edited.
            operations: Operations to apply in order.
            expected_revision: Revision the caller based the edit on. Optional for
                single UI edits, required for agent edits.
            reason: Optional free-text reason stored with the change set.
            agent_run_id: Agent run that produced the edit, for traceability.

        Returns:
            New revision, affected segment ids, and the diff.

        Raises:
            PermissionDeniedError: If the actor cannot edit the meeting.
            ConflictError: With code ``TRANSCRIPT_REVISION_CONFLICT`` on a stale revision.
            ValidationFailedError: If operations are invalid or change nothing.
        """
        await self.access_policy.require(actor, meeting_id, Permission.EDIT)
        meeting = await self._lock_meeting(meeting_id)
        if actor.via == "agent" and expected_revision is None:
            raise ValidationFailedError(
                "Agent edits must state the transcript revision they are based on.",
                code="EXPECTED_REVISION_REQUIRED",
            )
        self._check_revision(meeting, expected_revision)

        rows = await self._load_rows(meeting_id)
        changes = self._plan(rows, operations)
        summary = describe(operations, changes)
        if reason:
            summary = f"{summary}: {reason}"

        change_set = await self._record(
            meeting,
            actor,
            changes,
            summary=summary,
            operations=[op.model_dump(mode="json") for op in operations],
            agent_run_id=agent_run_id,
        )
        await self._persist(meeting_id, rows, changes)
        await self.events.publish(TranscriptEdited(meeting_id, meeting.transcript_revision, change_set.id))
        return self._result(change_set, changes, summary, base_revision=meeting.transcript_revision - 1)

    async def preview(
        self,
        actor: Actor,
        meeting_id: uuid.UUID,
        operations: Sequence[TranscriptOperation],
    ) -> TranscriptDiff:
        """Compute the diff of operations without writing anything.

        Args:
            actor: Identity previewing the edit.
            meeting_id: Meeting being edited.
            operations: Operations to simulate.

        Returns:
            Diff against the current transcript, including the base revision.

        Raises:
            PermissionDeniedError: If the actor cannot edit the meeting.
            ValidationFailedError: If operations are invalid or change nothing.
        """
        meeting = await self.access_policy.require(actor, meeting_id, Permission.EDIT)
        changes = self._plan(await self._load_rows(meeting_id), operations)
        return TranscriptDiff(changes, describe(operations, changes), meeting.transcript_revision)

    async def revert(
        self, actor: Actor, meeting_id: uuid.UUID, change_set_id: uuid.UUID
    ) -> ChangeSetResult:
        """Undo a change set by applying its inverse as a new change set.

        The inverse is only applied when every touched segment is still exactly as
        the original change left it, so a later edit is never silently overwritten.

        Args:
            actor: Identity reverting.
            meeting_id: Meeting being edited.
            change_set_id: Change set to undo.

        Returns:
            The new change set that restores the previous text.

        Raises:
            NotFoundError: If the change set does not belong to the meeting.
            ConflictError: If it was already reverted or later edits touched the same segments.
        """
        await self.access_policy.require(actor, meeting_id, Permission.EDIT)
        meeting = await self._lock_meeting(meeting_id)
        original = await self._get_change_set(meeting_id, change_set_id)

        already = await self.session.scalar(
            select(TranscriptChangeSetModel.id).where(
                TranscriptChangeSetModel.reverts_change_set_id == original.id
            )
        )
        if already is not None:
            raise ConflictError("This change was already reverted.", code="ALREADY_REVERTED")

        rows = await self._load_rows(meeting_id)
        by_id = {row.id: row for row in rows}
        occupied_orders = {row.sequence_order for row in rows}
        inverse: list[PlannedChange] = []
        for change in original.changes:
            current = by_id.get(change.segment_id)
            if change.op == "delete":
                free = change.before["sequence_order"] not in occupied_orders
                if current is not None or not free:
                    raise ConflictError(
                        "A later edit conflicts with undoing this change.", code=REVERT_CONFLICT
                    )
                inverse.append(PlannedChange("insert", change.segment_id, None, change.before))
                continue
            if current is None or not self._matches(current, change.after):
                raise ConflictError(
                    "A later edit conflicts with undoing this change.", code=REVERT_CONFLICT
                )
            if change.op == "insert":
                inverse.append(PlannedChange("delete", change.segment_id, change.after, None))
            else:
                inverse.append(PlannedChange("update", change.segment_id, change.after, change.before))

        summary = f"revert of revision {original.revision}"
        change_set = await self._record(
            meeting, actor, inverse, summary=summary, operations=[], reverts=original.id
        )
        await self._persist(meeting.id, rows, inverse)
        await self.events.publish(TranscriptEdited(meeting.id, meeting.transcript_revision, change_set.id))
        return self._result(change_set, inverse, summary, base_revision=meeting.transcript_revision - 1)

    async def list_change_sets(
        self, actor: Actor, meeting_id: uuid.UUID, limit: int = 50
    ) -> list[tuple[TranscriptChangeSetModel, bool]]:
        """List the transcript history, newest first.

        Args:
            actor: Identity requesting the history.
            meeting_id: Meeting whose history to read.
            limit: Maximum entries.

        Returns:
            Pairs of change set and whether a later change set reverted it.
        """
        await self.access_policy.require(actor, meeting_id, Permission.VIEW)
        sets = (
            await self.session.scalars(
                select(TranscriptChangeSetModel)
                .where(TranscriptChangeSetModel.meeting_id == meeting_id)
                .order_by(TranscriptChangeSetModel.revision.desc())
                .limit(limit)
            )
        ).all()
        reverted_ids = set(
            await self.session.scalars(
                select(TranscriptChangeSetModel.reverts_change_set_id).where(
                    TranscriptChangeSetModel.meeting_id == meeting_id,
                    TranscriptChangeSetModel.reverts_change_set_id.is_not(None),
                )
            )
        )
        return [(cs, cs.id in reverted_ids) for cs in sets]

    async def get_change_set(
        self, actor: Actor, meeting_id: uuid.UUID, change_set_id: uuid.UUID
    ) -> tuple[TranscriptChangeSetModel, bool]:
        """Return one change set with its segment changes.

        Args:
            actor: Identity requesting it.
            meeting_id: Meeting the change set belongs to.
            change_set_id: Change set id.

        Returns:
            The change set and whether it was reverted.

        Raises:
            NotFoundError: If it does not exist in this meeting.
        """
        await self.access_policy.require(actor, meeting_id, Permission.VIEW)
        change_set = await self._get_change_set(meeting_id, change_set_id)
        reverted = await self.session.scalar(
            select(TranscriptChangeSetModel.id).where(
                TranscriptChangeSetModel.reverts_change_set_id == change_set.id
            )
        )
        return change_set, reverted is not None

    async def _lock_meeting(self, meeting_id: uuid.UUID) -> MeetingModel:
        meeting = await self.session.scalar(
            select(MeetingModel)
            .where(MeetingModel.id == meeting_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if meeting is None:
            raise NotFoundError("Meeting not found.", code="MEETING_NOT_FOUND")
        return meeting

    @staticmethod
    def _check_revision(meeting: MeetingModel, expected_revision: int | None) -> None:
        if expected_revision is not None and expected_revision != meeting.transcript_revision:
            raise ConflictError(
                f"The transcript changed (now revision {meeting.transcript_revision}, "
                f"you edited revision {expected_revision}).",
                code=REVISION_CONFLICT,
            )

    async def _load_rows(self, meeting_id: uuid.UUID) -> list[TranscriptSegmentModel]:
        result = await self.session.scalars(
            select(TranscriptSegmentModel)
            .where(TranscriptSegmentModel.meeting_id == meeting_id)
            .order_by(TranscriptSegmentModel.sequence_order)
            .execution_options(populate_existing=True)
        )
        return list(result.all())

    @staticmethod
    def _plan(
        rows: Sequence[TranscriptSegmentModel], operations: Sequence[TranscriptOperation]
    ) -> list[PlannedChange]:
        states = [
            SegmentState(
                id=r.id,
                speaker_label=r.speaker_label,
                start_time=r.start_time,
                end_time=r.end_time,
                content=r.content,
                sequence_order=r.sequence_order,
            )
            for r in rows
        ]
        changes = TranscriptPlanner(states).plan(operations)
        if not any(not change.order_only for change in changes):
            raise ValidationFailedError(
                "The operations would not change the transcript.", code="NO_CHANGES"
            )
        return changes

    async def _record(
        self,
        meeting: MeetingModel,
        actor: Actor,
        changes: Sequence[PlannedChange],
        summary: str,
        operations: list[dict],
        agent_run_id: uuid.UUID | None = None,
        reverts: uuid.UUID | None = None,
    ) -> TranscriptChangeSetModel:
        meeting.transcript_revision += 1
        change_set = TranscriptChangeSetModel(
            meeting_id=meeting.id,
            revision=meeting.transcript_revision,
            actor_type="agent" if actor.via == "agent" else "user",
            actor_user_id=actor.user_id,
            agent_run_id=agent_run_id,
            reverts_change_set_id=reverts,
            summary=summary,
            operations=operations,
        )
        change_set.changes = [
            TranscriptSegmentChangeModel(
                segment_id=c.segment_id, op=c.kind, before=c.before, after=c.after
            )
            for c in changes
        ]
        self.session.add(change_set)
        await self.session.flush()
        return change_set

    async def _persist(
        self,
        meeting_id: uuid.UUID,
        rows: Sequence[TranscriptSegmentModel],
        changes: Sequence[PlannedChange],
    ) -> None:
        """Write segment changes, parking moved rows on temporary orders to satisfy the unique key."""
        by_id = {row.id: row for row in rows}

        for change in changes:
            if change.kind == "delete":
                await self.session.delete(by_id[change.segment_id])
        await self.session.flush()

        updates = [c for c in changes if c.kind == "update"]
        for change in updates:
            if change.before["sequence_order"] != change.after["sequence_order"]:
                by_id[change.segment_id].sequence_order = -change.after["sequence_order"] - 1
        await self.session.flush()

        for change in updates:
            row = by_id[change.segment_id]
            after = change.after
            row.speaker_label = after["speaker_label"]
            row.start_time = after["start_time"]
            row.end_time = after["end_time"]
            row.content = after["content"]
            row.sequence_order = after["sequence_order"]
            if not change.order_only:
                row.version += 1
        await self.session.flush()

        for change in changes:
            if change.kind == "insert":
                after = change.after
                self.session.add(
                    TranscriptSegmentModel(
                        id=change.segment_id,
                        meeting_id=meeting_id,
                        speaker_label=after["speaker_label"],
                        start_time=after["start_time"],
                        end_time=after["end_time"],
                        content=after["content"],
                        sequence_order=after["sequence_order"],
                    )
                )
        await self.session.flush()

    @staticmethod
    def _matches(row: TranscriptSegmentModel, snapshot: dict) -> bool:
        return all(getattr(row, field) == snapshot[field] for field in SNAPSHOT_FIELDS)

    async def _get_change_set(
        self, meeting_id: uuid.UUID, change_set_id: uuid.UUID
    ) -> TranscriptChangeSetModel:
        change_set = await self.session.scalar(
            select(TranscriptChangeSetModel).where(
                TranscriptChangeSetModel.id == change_set_id,
                TranscriptChangeSetModel.meeting_id == meeting_id,
            )
        )
        if change_set is None:
            raise NotFoundError("Change set not found.", code="CHANGE_SET_NOT_FOUND")
        await self.session.refresh(change_set, ["changes"])
        return change_set

    @staticmethod
    def _result(
        change_set: TranscriptChangeSetModel,
        changes: Sequence[PlannedChange],
        summary: str,
        base_revision: int,
    ) -> ChangeSetResult:
        return ChangeSetResult(
            change_set_id=change_set.id,
            revision=change_set.revision,
            affected_segment_ids=[c.segment_id for c in changes if not c.order_only],
            diff=TranscriptDiff(list(changes), summary, base_revision),
        )
