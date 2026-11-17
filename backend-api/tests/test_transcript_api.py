import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.processing_job import ProcessingJobModel
from app.models.transcript import TranscriptSegmentModel
from tests.conftest import MakeMeeting, RegisterUser


async def seeded(db: AsyncSession, make_meeting: MakeMeeting, owner_id, **meeting_kwargs):
    meeting = await make_meeting(owner_id, **meeting_kwargs)
    segments = []
    for order, (speaker, text) in enumerate(
        [("Speaker 1", "Họp về Gemany."), ("Speaker 2", "Gemany rất tốt."), ("Speaker 1", "Kết thúc.")],
        start=1,
    ):
        segment = TranscriptSegmentModel(
            meeting_id=meeting.id, speaker_label=speaker, start_time=order * 10.0,
            end_time=order * 10.0 + 5, content=text, sequence_order=order,
        )
        db.add(segment)
        segments.append(segment)
    await db.flush()
    return meeting, segments


@pytest.mark.asyncio
async def test_batch_operations_apply_preview_history_and_revert(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting, db_session: AsyncSession
) -> None:
    owner = await register_user("owner@example.com")
    meeting, segments = await seeded(db_session, make_meeting, owner.id)
    base = f"/api/v1/meetings/{meeting.id}/transcript"
    body = {
        "operations": [
            {"op": "replace_text", "find": "Gemany", "replace": "Gemini"},
            {"op": "rename_speaker", "old_label": "Speaker 1", "new_label": "Linh"},
        ],
        "expected_revision": 0,
        "reason": "fix names",
    }

    preview = await client.post(f"{base}/operations:preview", headers=owner.headers, json={"operations": body["operations"]})
    assert preview.status_code == 200 and preview.json()["base_revision"] == 0
    assert len(preview.json()["changes"]) == 3
    assert (await client.get(base, headers=owner.headers)).json()[0]["content"] == "Họp về Gemany."

    applied = await client.post(f"{base}/operations", headers=owner.headers, json=body)
    assert applied.status_code == 200, applied.text
    assert applied.json()["revision"] == 1 and len(applied.json()["affected_segment_ids"]) == 3
    current = (await client.get(base, headers=owner.headers)).json()
    assert [s["content"] for s in current] == ["Họp về Gemini.", "Gemini rất tốt.", "Kết thúc."]
    assert [s["speaker_label"] for s in current] == ["Linh", "Speaker 2", "Linh"]
    assert all(s["version"] == 2 for s in current[:2])

    history = (await client.get(f"{base}/change-sets", headers=owner.headers)).json()
    assert len(history) == 1 and history[0]["actor_type"] == "user" and "fix names" in history[0]["summary"]
    detail = await client.get(f"{base}/change-sets/{history[0]['id']}", headers=owner.headers)
    assert len(detail.json()["changes"]) == 3 and detail.json()["operations"][0]["op"] == "replace_text"

    reverted = await client.post(f"{base}/change-sets/{history[0]['id']}/revert", headers=owner.headers)
    assert reverted.status_code == 200 and reverted.json()["revision"] == 2
    restored = (await client.get(base, headers=owner.headers)).json()
    assert [s["content"] for s in restored] == ["Họp về Gemany.", "Gemany rất tốt.", "Kết thúc."]
    again = await client.post(f"{base}/change-sets/{history[0]['id']}/revert", headers=owner.headers)
    assert again.status_code == 409 and again.json()["error"]["code"] == "ALREADY_REVERTED"


@pytest.mark.asyncio
async def test_stale_revision_returns_409_and_invalid_operations_422(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting, db_session: AsyncSession
) -> None:
    owner = await register_user("owner@example.com")
    meeting, segments = await seeded(db_session, make_meeting, owner.id)
    url = f"/api/v1/meetings/{meeting.id}/transcript/operations"
    ops = [{"op": "update_text", "segment_id": str(segments[0].id), "new_text": "Mới."}]

    assert (await client.post(url, headers=owner.headers, json={"operations": ops, "expected_revision": 0})).status_code == 200
    stale = await client.post(url, headers=owner.headers, json={"operations": ops, "expected_revision": 0})
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "TRANSCRIPT_REVISION_CONFLICT"

    unknown = await client.post(url, headers=owner.headers, json={"operations": [
        {"op": "delete_segments", "segment_ids": ["00000000-0000-0000-0000-000000000042"]}
    ]})
    assert unknown.status_code == 422 and unknown.json()["error"]["code"] == "SEGMENT_NOT_FOUND"

    bad_shape = await client.post(url, headers=owner.headers, json={"operations": [{"op": "explode"}]})
    assert bad_shape.status_code == 422
    too_many = await client.post(url, headers=owner.headers, json={"operations": ops * 201})
    assert too_many.status_code == 422


@pytest.mark.asyncio
async def test_viewers_can_read_history_but_cannot_edit_or_revert(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting, db_session: AsyncSession
) -> None:
    owner = await register_user("owner@example.com")
    meeting, segments = await seeded(
        db_session, make_meeting, owner.id, share_token="guest-viewer-token-123456", share_permission="viewer"
    )
    base = f"/api/v1/meetings/{meeting.id}/transcript"
    ops = {"operations": [{"op": "update_text", "segment_id": str(segments[0].id), "new_text": "x"}]}
    applied = await client.post(f"{base}/operations", headers=owner.headers, json=ops)
    change_set_id = applied.json()["change_set_id"]
    guest = "?share=guest-viewer-token-123456"

    assert (await client.get(f"{base}/change-sets{guest}")).status_code == 200
    assert (await client.post(f"{base}/operations{guest}", json=ops)).status_code == 403
    assert (await client.post(f"{base}/operations:preview{guest}", json=ops)).status_code == 403
    assert (await client.post(f"{base}/change-sets/{change_set_id}/revert{guest}")).status_code == 403


@pytest.mark.asyncio
async def test_legacy_edit_endpoints_go_through_the_editor_and_keep_their_shapes(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting, db_session: AsyncSession
) -> None:
    owner = await register_user("owner@example.com")
    meeting, segments = await seeded(db_session, make_meeting, owner.id)
    base = f"/api/v1/meetings/{meeting.id}/transcript"

    edited = await client.patch(
        f"{base}/segments/{segments[0].id}", headers=owner.headers,
        json={"content": "Nội dung mới", "speaker_label": "Linh"},
    )
    assert edited.status_code == 200
    assert (edited.json()["content"], edited.json()["speaker_label"]) == ("Nội dung mới", "Linh")

    unchanged = await client.patch(
        f"{base}/segments/{segments[0].id}", headers=owner.headers, json={"content": "Nội dung mới"}
    )
    assert unchanged.status_code == 200

    renamed = await client.post(
        f"{base}/rename-speaker", headers=owner.headers,
        json={"old_speaker_label": "Speaker 2", "new_speaker_label": "Dũng"},
    )
    assert renamed.json() == {"affected_segments": 1, "new_speaker_label": "Dũng"}
    deleted = await client.post(
        f"{base}/delete-segments", headers=owner.headers, json={"segment_ids": [str(segments[2].id)]}
    )
    assert deleted.json() == {"deleted_segments": 1}

    history = (await client.get(f"{base}/change-sets", headers=owner.headers)).json()
    assert [h["revision"] for h in history] == [3, 2, 1]


@pytest.mark.asyncio
async def test_reindex_and_summary_regeneration_queue_jobs_for_ready_meetings(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting, db_session: AsyncSession
) -> None:
    owner = await register_user("owner@example.com")
    ready = await make_meeting(owner.id)
    busy = await make_meeting(owner.id, status="transcribing")

    index = await client.post(f"/api/v1/meetings/{ready.id}/reindex", headers=owner.headers)
    summary = await client.post(f"/api/v1/meetings/{ready.id}/summary:regenerate", headers=owner.headers)
    assert (index.status_code, index.json()) == (202, {"index_status": "pending"})
    assert (summary.status_code, summary.json()) == (202, {"summary_status": "pending"})
    kinds = sorted(j.kind for j in (await db_session.scalars(select(ProcessingJobModel))).all())
    assert kinds == ["index", "summarize"]

    for path in ("reindex", "summary:regenerate"):
        blocked = await client.post(f"/api/v1/meetings/{busy.id}/{path}", headers=owner.headers)
        assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "INVALID_MEETING_STATE"
