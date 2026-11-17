import re
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from app.core.errors import ValidationFailedError
from app.schemas.transcript_ops import (
    DeleteSegments,
    MergeSegments,
    ReassignSpeaker,
    RenameSpeaker,
    ReplaceText,
    SplitSegment,
    TranscriptOperation,
    UpdateText,
)

ChangeKind = Literal["update", "delete", "insert"]
SNAPSHOT_FIELDS = ("speaker_label", "start_time", "end_time", "content", "sequence_order")


@dataclass
class SegmentState:
    """In-memory copy of a transcript segment used while planning edits."""

    id: uuid.UUID
    speaker_label: str
    start_time: float
    end_time: float
    content: str
    sequence_order: int

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-friendly copy of the segment's editable state."""
        return {
            "id": str(self.id),
            "speaker_label": self.speaker_label,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "content": self.content,
            "sequence_order": self.sequence_order,
        }


@dataclass(frozen=True, slots=True)
class PlannedChange:
    """One segment-level change produced by planning operations.

    Attributes:
        kind: ``insert``, ``update`` or ``delete``.
        segment_id: Affected segment.
        before: Snapshot before the change, None for inserts.
        after: Snapshot after the change, None for deletes.
    """

    kind: ChangeKind
    segment_id: uuid.UUID
    before: dict[str, Any] | None
    after: dict[str, Any] | None

    @property
    def order_only(self) -> bool:
        """True when an update only moved the segment's position (a side effect of a split)."""
        if self.kind != "update" or self.before is None or self.after is None:
            return False
        return all(
            self.before[f] == self.after[f] for f in SNAPSHOT_FIELDS if f != "sequence_order"
        )


class TranscriptPlanner:
    """Pure planner turning transcript operations into segment-level changes.

    Works on in-memory copies, so the same code serves preview (no write), apply
    and tests, and never touches the database.
    """

    def __init__(
        self,
        segments: Sequence[SegmentState],
        new_id: Callable[[], uuid.UUID] = uuid.uuid4,
    ) -> None:
        """Initialize the planner.

        Args:
            segments: Current segments of the meeting.
            new_id: Factory for ids of segments created by splits.
        """
        self.working = sorted(
            (SegmentState(**vars(s)) for s in segments), key=lambda s: s.sequence_order
        )
        self.originals = {s.id: s.snapshot() for s in self.working}
        self.new_id = new_id

    def plan(self, operations: Sequence[TranscriptOperation]) -> list[PlannedChange]:
        """Apply operations in order to the working copy and diff against the original.

        Args:
            operations: Operations to apply, in order.

        Returns:
            Segment-level changes. Empty when nothing would change.

        Raises:
            ValidationFailedError: If an operation references unknown segments or invalid values.
        """
        handlers = {
            UpdateText: self._update_text,
            ReplaceText: self._replace_text,
            RenameSpeaker: self._rename_speaker,
            ReassignSpeaker: self._reassign_speaker,
            DeleteSegments: self._delete_segments,
            SplitSegment: self._split_segment,
            MergeSegments: self._merge_segments,
        }
        for operation in operations:
            handlers[type(operation)](operation)
        return self._diff()

    def _diff(self) -> list[PlannedChange]:
        final = {s.id: s.snapshot() for s in self.working}
        changes: list[PlannedChange] = []
        for segment_id, before in self.originals.items():
            after = final.get(segment_id)
            if after is None:
                changes.append(PlannedChange("delete", segment_id, before, None))
            elif after != before:
                changes.append(PlannedChange("update", segment_id, before, after))
        for segment_id, after in final.items():
            if segment_id not in self.originals:
                changes.append(PlannedChange("insert", segment_id, None, after))
        return changes

    def _find(self, segment_id: uuid.UUID) -> SegmentState:
        for segment in self.working:
            if segment.id == segment_id:
                return segment
        raise ValidationFailedError(
            f"Segment {segment_id} does not exist in this meeting.", code="SEGMENT_NOT_FOUND"
        )

    def _find_all(self, segment_ids: Sequence[uuid.UUID]) -> list[SegmentState]:
        return [self._find(segment_id) for segment_id in dict.fromkeys(segment_ids)]

    def _update_text(self, op: UpdateText) -> None:
        self._find(op.segment_id).content = op.new_text.strip()

    def _replace_text(self, op: ReplaceText) -> None:
        targets = (
            self._find_all(op.segment_ids or [])
            if op.scope == "segments"
            else list(self.working)
        )
        if op.scope == "segments" and not op.segment_ids:
            raise ValidationFailedError(
                "scope 'segments' needs segment_ids.", code="VALIDATION_FAILED"
            )
        escaped = re.escape(op.find)
        pattern = rf"(?<!\w){escaped}(?!\w)" if op.whole_word else escaped
        regex = re.compile(pattern, 0 if op.case_sensitive else re.IGNORECASE)
        for segment in targets:
            segment.content = regex.sub(lambda _m: op.replace, segment.content)

    def _rename_speaker(self, op: RenameSpeaker) -> None:
        old, new = op.old_label.strip(), op.new_label.strip()
        matched = [s for s in self.working if s.speaker_label == old]
        if not matched:
            raise ValidationFailedError(
                f"No segment is attributed to speaker '{old}'.", code="SPEAKER_NOT_FOUND"
            )
        for segment in matched:
            segment.speaker_label = new

    def _reassign_speaker(self, op: ReassignSpeaker) -> None:
        for segment in self._find_all(op.segment_ids):
            segment.speaker_label = op.new_label.strip()

    def _delete_segments(self, op: DeleteSegments) -> None:
        doomed = {s.id for s in self._find_all(op.segment_ids)}
        self.working = [s for s in self.working if s.id not in doomed]

    def _split_segment(self, op: SplitSegment) -> None:
        segment = self._find(op.segment_id)
        head, tail = segment.content[: op.at_char].strip(), segment.content[op.at_char :].strip()
        if not head or not tail:
            raise ValidationFailedError(
                "Splitting here would leave an empty segment.", code="INVALID_SPLIT"
            )
        if not segment.start_time < op.split_time < segment.end_time:
            raise ValidationFailedError(
                "split_time must fall inside the segment.", code="INVALID_SPLIT"
            )

        new_segment = SegmentState(
            id=self.new_id(),
            speaker_label=segment.speaker_label,
            start_time=op.split_time,
            end_time=segment.end_time,
            content=tail,
            sequence_order=segment.sequence_order + 1,
        )
        for other in self.working:
            if other.sequence_order > segment.sequence_order:
                other.sequence_order += 1
        segment.content, segment.end_time = head, op.split_time
        index = self.working.index(segment)
        self.working.insert(index + 1, new_segment)

    def _merge_segments(self, op: MergeSegments) -> None:
        selected = self._find_all(op.segment_ids)
        selected.sort(key=lambda s: s.sequence_order)
        if len(selected) < 2:
            raise ValidationFailedError("Merging needs at least two segments.", code="INVALID_MERGE")
        if len({s.speaker_label for s in selected}) > 1:
            raise ValidationFailedError(
                "Only segments of the same speaker can be merged.", code="INVALID_MERGE"
            )
        positions = [self.working.index(s) for s in selected]
        if positions != list(range(positions[0], positions[0] + len(positions))):
            raise ValidationFailedError(
                "Only adjacent segments can be merged.", code="INVALID_MERGE"
            )

        first = selected[0]
        first.content = " ".join(s.content for s in selected)
        first.start_time = min(s.start_time for s in selected)
        first.end_time = max(s.end_time for s in selected)
        removed = {s.id for s in selected[1:]}
        self.working = [s for s in self.working if s.id not in removed]
