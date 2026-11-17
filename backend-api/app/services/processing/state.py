from app.core.errors import InvalidStateError
from app.domain.enums import MeetingStatus
from app.models.meeting import MeetingModel

PROCESSING_STATES = frozenset(
    {MeetingStatus.TRANSCRIBING, MeetingStatus.SUMMARIZING, MeetingStatus.INDEXING}
)

ALLOWED_TRANSITIONS: dict[MeetingStatus, frozenset[MeetingStatus]] = {
    MeetingStatus.DRAFT: frozenset({MeetingStatus.UPLOADED}),
    MeetingStatus.UPLOADED: frozenset(
        {MeetingStatus.UPLOADED, MeetingStatus.TRANSCRIBING, MeetingStatus.FAILED}
    ),
    MeetingStatus.TRANSCRIBING: frozenset({MeetingStatus.SUMMARIZING, MeetingStatus.FAILED}),
    MeetingStatus.SUMMARIZING: frozenset(
        {MeetingStatus.INDEXING, MeetingStatus.READY, MeetingStatus.FAILED}
    ),
    MeetingStatus.INDEXING: frozenset({MeetingStatus.READY, MeetingStatus.FAILED}),
    MeetingStatus.READY: frozenset({MeetingStatus.UPLOADED, MeetingStatus.TRANSCRIBING}),
    MeetingStatus.FAILED: frozenset({MeetingStatus.UPLOADED, MeetingStatus.TRANSCRIBING}),
}


def transition(
    meeting: MeetingModel,
    to: MeetingStatus,
    failure_stage: str | None = None,
    failure_reason: str | None = None,
) -> None:
    """Move a meeting to a new processing state, enforcing the transition table.

    Entering ``failed`` records the stage and reason. Leaving ``failed`` clears them.

    Args:
        meeting: Meeting to update in place.
        to: Target state.
        failure_stage: Pipeline stage that failed, only used when ``to`` is ``failed``.
        failure_reason: Human-readable failure cause, only used when ``to`` is ``failed``.

    Raises:
        InvalidStateError: If the move is not allowed from the current state.
    """
    current = MeetingStatus(meeting.status)
    if to not in ALLOWED_TRANSITIONS.get(current, frozenset()):
        raise InvalidStateError(
            f"Meeting cannot move from '{current}' to '{to}'.", code="INVALID_MEETING_STATE"
        )

    meeting.status = to
    if to == MeetingStatus.FAILED:
        meeting.failure_stage = failure_stage
        meeting.failure_reason = failure_reason
    else:
        meeting.failure_stage = None
        meeting.failure_reason = None
