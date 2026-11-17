import uuid

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, PermissionDeniedError, ValidationFailedError
from app.domain.actor import Actor
from app.models.outbox import OutboxEventModel
from app.models.processing_job import ProcessingJobModel
from app.models.transcript import TranscriptSegmentModel
from app.models.transcript_revision import TranscriptChangeSetModel
from app.schemas.transcript_ops import (
    DeleteSegments,
    MergeSegments,
    ReassignSpeaker,
    RenameSpeaker,
    ReplaceText,
    SplitSegment,
    UpdateText,
)
from app.services.access_policy import MeetingAccessPolicy
from app.services.event_bus import build_event_bus
from app.services.transcript_editor import TranscriptEditor
from tests.conftest import MakeMeeting, RegisterUser

ROWS = [
    ("Speaker 1", 0, 10, "Xin chào, hôm nay họp về Gemany."),
    ("Speaker 1", 10, 20, "Gemany là nhà cung cấp mô hình."),
    ("Speaker 2", 20, 30, "Đồng ý, ta dùng Gemany."),
    ("Speaker 2", 30, 40, "Hẹn gặp lại."),
]


async def snapshot(db: AsyncSession, meeting_id: uuid.UUID) -> list[tuple]:
    rows = (
        await db.scalars(
            select(TranscriptSegmentModel)
            .where(TranscriptSegmentModel.meeting_id == meeting_id)
            .order_by(TranscriptSegmentModel.sequence_order)
            .execution_options(populate_existing=True)
        )
    ).all()
    return [(r.id, r.speaker_label, r.start_time, r.end_time, r.content, r.sequence_order) for r in rows]


@pytest_asyncio.fixture(loop_scope="function")
async def world(db_session: AsyncSession, make_meeting: MakeMeeting, register_user: RegisterUser):
    owner = await register_user("owner@example.com")
    meeting = await make_meeting(owner.id, share_token="viewer-token-1234567890", share_permission="viewer")
    for order, (speaker, start, end, text) in enumerate(ROWS, start=1):
        db_session.add(
            TranscriptSegmentModel(
                meeting_id=meeting.id, speaker_label=speaker, start_time=start,
                end_time=end, content=text, sequence_order=order,
            )
        )
    await db_session.flush()
    ids = [s[0] for s in await snapshot(db_session, meeting.id)]
    editor = TranscriptEditor(db_session, MeetingAccessPolicy(db_session), build_event_bus(db_session))
    return {"owner": Actor(user_id=owner.id), "meeting": meeting, "ids": ids, "editor": editor}


async def apply_and_revert(world, db, operations):
    before = await snapshot(db, world["meeting"].id)
    applied = await world["editor"].apply(world["owner"], world["meeting"].id, operations, None)
    changed = await snapshot(db, world["meeting"].id)
    assert changed != before
    reverted = await world["editor"].revert(world["owner"], world["meeting"].id, applied.change_set_id)
    after = await snapshot(db, world["meeting"].id)
    return before, changed, after, applied, reverted


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "build",
    [
        lambda ids: [UpdateText(segment_id=ids[3], new_text="Hẹn gặp lại sau nhé.")],
        lambda ids: [ReplaceText(find="gemany", replace="Gemini")],
        lambda ids: [RenameSpeaker(old_label="Speaker 1", new_label="Linh")],
        lambda ids: [ReassignSpeaker(segment_ids=[ids[1]], new_label="Dũng")],
        lambda ids: [DeleteSegments(segment_ids=[ids[1], ids[2]])],
        lambda ids: [SplitSegment(segment_id=ids[1], at_char=10, split_time=15.0)],
        lambda ids: [MergeSegments(segment_ids=[ids[2], ids[3]])],
        lambda ids: [
            RenameSpeaker(old_label="Speaker 2", new_label="Dũng"),
            ReplaceText(find="Gemany", replace="Gemini"),
            DeleteSegments(segment_ids=[ids[0]]),
        ],
    ],
    ids=["update", "replace", "rename", "reassign", "delete", "split", "merge", "batch"],
)
async def test_every_operation_applies_and_reverts_to_the_exact_previous_state(
    world, db_session: AsyncSession, build
) -> None:
    before, changed, after, applied, reverted = await apply_and_revert(
        world, db_session, build(world["ids"])
    )

    assert after == before
    assert applied.revision == 1 and reverted.revision == 2
    assert world["meeting"].transcript_revision == 2
    assert changed != after


@pytest.mark.asyncio
async def test_apply_records_history_versions_and_actor(world, db_session: AsyncSession) -> None:
    ids = world["ids"]
    result = await world["editor"].apply(
        world["owner"], world["meeting"].id,
        [UpdateText(segment_id=ids[0], new_text="Mở đầu mới.")], None, reason="fix typo",
    )

    change_set = await db_session.get(TranscriptChangeSetModel, result.change_set_id)
    await db_session.refresh(change_set, ["changes"])
    assert (change_set.revision, change_set.actor_type, change_set.actor_user_id) == (
        1, "user", world["owner"].user_id,
    )
    assert "fix typo" in change_set.summary and change_set.operations[0]["op"] == "update_text"
    assert [(c.op, c.segment_id) for c in change_set.changes] == [("update", ids[0])]
    row = await db_session.get(TranscriptSegmentModel, ids[0])
    assert row.version == 2 and result.affected_segment_ids == [ids[0]]


@pytest.mark.asyncio
async def test_stale_expected_revision_is_a_conflict_and_changes_nothing(
    world, db_session: AsyncSession
) -> None:
    ids, editor = world["ids"], world["editor"]
    await editor.apply(world["owner"], world["meeting"].id, [UpdateText(segment_id=ids[0], new_text="Một.")], 0)

    before = await snapshot(db_session, world["meeting"].id)
    with pytest.raises(ConflictError) as exc:
        await editor.apply(
            world["owner"], world["meeting"].id, [UpdateText(segment_id=ids[1], new_text="Hai.")], 0
        )
    assert exc.value.code == "TRANSCRIPT_REVISION_CONFLICT"
    assert await snapshot(db_session, world["meeting"].id) == before


@pytest.mark.asyncio
async def test_agent_edits_must_state_their_base_revision(world) -> None:
    agent = Actor(user_id=world["owner"].user_id, via="agent")
    with pytest.raises(ValidationFailedError) as exc:
        await world["editor"].apply(
            agent, world["meeting"].id, [UpdateText(segment_id=world["ids"][0], new_text="x")], None
        )
    assert exc.value.code == "EXPECTED_REVISION_REQUIRED"

    result = await world["editor"].apply(
        agent, world["meeting"].id, [UpdateText(segment_id=world["ids"][0], new_text="x")], 0
    )
    assert result.revision == 1


@pytest.mark.asyncio
async def test_agent_actor_is_recorded_as_agent(world, db_session: AsyncSession) -> None:
    agent = Actor(user_id=world["owner"].user_id, via="agent")
    run_id = uuid.uuid4()
    result = await world["editor"].apply(
        agent, world["meeting"].id, [UpdateText(segment_id=world["ids"][0], new_text="y")], 0,
        agent_run_id=run_id,
    )
    change_set = await db_session.get(TranscriptChangeSetModel, result.change_set_id)
    assert (change_set.actor_type, change_set.agent_run_id) == ("agent", run_id)


@pytest.mark.asyncio
async def test_viewers_cannot_edit_preview_or_revert(world) -> None:
    viewer = Actor(share_token="viewer-token-1234567890", via="share")
    operations = [UpdateText(segment_id=world["ids"][0], new_text="hack")]
    editor, meeting_id = world["editor"], world["meeting"].id

    with pytest.raises(PermissionDeniedError):
        await editor.apply(viewer, meeting_id, operations, None)
    with pytest.raises(PermissionDeniedError):
        await editor.preview(viewer, meeting_id, operations)
    applied = await editor.apply(world["owner"], meeting_id, operations, None)
    with pytest.raises(PermissionDeniedError):
        await editor.revert(viewer, meeting_id, applied.change_set_id)
    assert len(await editor.list_change_sets(viewer, meeting_id)) == 1


@pytest.mark.asyncio
async def test_preview_never_writes(world, db_session: AsyncSession) -> None:
    before = await snapshot(db_session, world["meeting"].id)
    diff = await world["editor"].preview(
        world["owner"], world["meeting"].id, [ReplaceText(find="Gemany", replace="Gemini")]
    )

    assert len(diff.changes) == 3 and diff.base_revision == 0
    assert await snapshot(db_session, world["meeting"].id) == before
    assert world["meeting"].transcript_revision == 0
    assert await db_session.scalar(select(func.count()).select_from(TranscriptChangeSetModel)) == 0


@pytest.mark.asyncio
async def test_operations_that_change_nothing_are_rejected(world) -> None:
    with pytest.raises(ValidationFailedError) as exc:
        await world["editor"].apply(
            world["owner"], world["meeting"].id,
            [ReplaceText(find="khong-co", replace="x")], None,
        )
    assert exc.value.code == "NO_CHANGES"
    assert world["meeting"].transcript_revision == 0


@pytest.mark.asyncio
async def test_revert_refuses_to_overwrite_a_later_edit_and_cannot_run_twice(
    world, db_session: AsyncSession
) -> None:
    ids, editor, owner, meeting_id = world["ids"], world["editor"], world["owner"], world["meeting"].id
    first = await editor.apply(owner, meeting_id, [UpdateText(segment_id=ids[0], new_text="Bản một.")], None)
    await editor.apply(owner, meeting_id, [UpdateText(segment_id=ids[0], new_text="Bản hai.")], None)

    with pytest.raises(ConflictError) as exc:
        await editor.revert(owner, meeting_id, first.change_set_id)
    assert exc.value.code == "TRANSCRIPT_REVERT_CONFLICT"

    standalone = await editor.apply(owner, meeting_id, [UpdateText(segment_id=ids[3], new_text="Khác.")], None)
    await editor.revert(owner, meeting_id, standalone.change_set_id)
    with pytest.raises(ConflictError) as again:
        await editor.revert(owner, meeting_id, standalone.change_set_id)
    assert again.value.code == "ALREADY_REVERTED"

    history = {cs.id: reverted for cs, reverted in await editor.list_change_sets(owner, meeting_id)}
    assert history[standalone.change_set_id] is True and history[first.change_set_id] is False


@pytest.mark.asyncio
async def test_edit_marks_summary_and_index_stale_and_queues_one_delayed_reindex(
    world, db_session: AsyncSession
) -> None:
    meeting, ids, editor, owner = world["meeting"], world["ids"], world["editor"], world["owner"]
    assert (meeting.summary_status, meeting.index_status) == ("ready", "ready")

    first = await editor.apply(owner, meeting.id, [UpdateText(segment_id=ids[0], new_text="Một.")], None)
    assert (meeting.summary_status, meeting.index_status) == ("stale", "stale")

    second = await editor.apply(owner, meeting.id, [UpdateText(segment_id=ids[1], new_text="Hai.")], None)

    jobs = (await db_session.scalars(select(ProcessingJobModel))).all()
    assert sorted(j.idempotency_key for j in jobs) == sorted(
        [f"index:{meeting.id}:{first.revision}"]
    )
    events = (await db_session.scalars(select(OutboxEventModel))).all()
    assert len(events) == 1 and events[0].available_at is not None
    assert second.revision == 2


@pytest.mark.asyncio
async def test_list_and_get_change_sets(world, db_session: AsyncSession) -> None:
    ids, editor, owner, meeting_id = world["ids"], world["editor"], world["owner"], world["meeting"].id
    one = await editor.apply(owner, meeting_id, [UpdateText(segment_id=ids[0], new_text="A.")], None)
    two = await editor.apply(owner, meeting_id, [DeleteSegments(segment_ids=[ids[3]])], None)

    listed = await editor.list_change_sets(owner, meeting_id)
    assert [cs.id for cs, _ in listed] == [two.change_set_id, one.change_set_id]

    detail, reverted = await editor.get_change_set(owner, meeting_id, two.change_set_id)
    assert reverted is False and [(c.op, c.segment_id) for c in detail.changes] == [("delete", ids[3])]
