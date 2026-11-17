import uuid
from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import _encode_token, create_agent_token
from app.models.agent import AgentActionModel
from app.models.transcript import TranscriptSegmentModel
from app.models.transcript_revision import TranscriptChangeSetModel
from app.services.retrieval_service import RetrievedChunk
from tests.agent_helpers import delegated_headers, propose, seed_meeting
from tests.conftest import FakeRetriever, MakeMeeting, RegisterUser, UpgradeToPro

BASE = "/internal/agent/v1/meetings"


@pytest.mark.asyncio
async def test_both_credentials_are_required_and_ordinary_tokens_are_rejected(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting, db_session: AsyncSession,
) -> None:
    owner = await register_user("owner@example.com")
    meeting, _ = await seed_meeting(db_session, make_meeting, owner.id)
    good = await delegated_headers(db_session, owner, meeting)
    url = f"{BASE}/{meeting.id}/overview"

    assert (await client.get(url, headers={"Authorization": good["Authorization"]})).status_code == 401
    wrong_service = {**good, "X-Service-Token": "not-the-service-token"}
    assert (await client.get(url, headers=wrong_service)).status_code == 401
    assert (await client.get(url, headers={"X-Service-Token": good["X-Service-Token"]})).status_code == 401
    # a user's normal access token must not work as a delegated token, nor the other way round
    as_access = {"Authorization": owner.headers["Authorization"], "X-Service-Token": good["X-Service-Token"]}
    assert (await client.get(url, headers=as_access)).status_code == 401
    delegated_on_public_api = await client.get(
        "/api/v1/auth/me", headers={"Authorization": good["Authorization"]}
    )
    assert delegated_on_public_api.status_code == 401
    assert (await client.get(url, headers=good)).status_code == 200


@pytest.mark.asyncio
async def test_public_internet_cannot_reach_tools_without_the_shared_service_token(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting, db_session: AsyncSession,
) -> None:
    owner = await register_user("owner@example.com")
    meeting, _ = await seed_meeting(db_session, make_meeting, owner.id)
    response = await client.get(f"{BASE}/{meeting.id}/overview", headers=owner.headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_SERVICE_TOKEN"


@pytest.mark.asyncio
async def test_a_token_for_meeting_a_cannot_call_tools_on_meeting_b(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting, db_session: AsyncSession,
) -> None:
    owner = await register_user("owner@example.com")
    meeting_a, _ = await seed_meeting(db_session, make_meeting, owner.id)
    meeting_b, _ = await seed_meeting(db_session, make_meeting, owner.id)
    headers = await delegated_headers(db_session, owner, meeting_a)

    for method, path, body in [
        ("GET", "overview", None),
        ("GET", "segments", None),
        ("GET", "summary", None),
        ("POST", "find", {"pattern": "x"}),
        ("POST", "search", {"query": "x"}),
        ("POST", "agent-actions", {"kind": "summary_regenerate", "base_revision": 0}),
        ("POST", "artifacts", {"kind": "srt", "title": "t"}),
    ]:
        response = await client.request(method, f"{BASE}/{meeting_b.id}/{path}", headers=headers, json=body)
        assert response.status_code == 403, path
        assert response.json()["error"]["code"] == "AGENT_SCOPE_MISMATCH"


@pytest.mark.asyncio
async def test_expired_stale_and_foreign_conversation_tokens_are_rejected(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting, db_session: AsyncSession,
) -> None:
    owner = await register_user("owner@example.com")
    other = await register_user("other@example.com")
    meeting, _ = await seed_meeting(db_session, make_meeting, owner.id)
    headers = await delegated_headers(db_session, owner, meeting)
    url = f"{BASE}/{meeting.id}/overview"
    service = headers["X-Service-Token"]

    claims = {
        "sub": str(owner.id), "aud": "agent", "scope": f"meeting:{meeting.id}",
        "conv": str(uuid.uuid4()), "tv": 0,
    }
    expired = _encode_token(claims, "agent", timedelta(seconds=-5))
    assert (await client.get(url, headers={"Authorization": f"Bearer {expired}", "X-Service-Token": service})).status_code == 401

    unknown_conversation = _encode_token(claims, "agent", timedelta(minutes=5))
    assert (await client.get(url, headers={"Authorization": f"Bearer {unknown_conversation}", "X-Service-Token": service})).status_code == 401

    others_headers = await delegated_headers(db_session, other, meeting)
    forged = create_agent_token(owner.id, meeting.id, uuid.UUID(_conversation_of(others_headers)), 0)
    assert (await client.get(url, headers={"Authorization": f"Bearer {forged}", "X-Service-Token": service})).status_code == 401

    changed = await client.post(
        "/api/v1/users/me/change-password", headers=owner.headers,
        json={"old_password": "Password123!", "new_password": "NewPassword456!"},
    )
    assert changed.status_code == 200
    assert (await client.get(url, headers=headers)).status_code == 401


def _conversation_of(headers: dict[str, str]) -> str:
    from app.core.security import decode_agent_token

    return decode_agent_token(headers["Authorization"].removeprefix("Bearer "))["conv"]


@pytest.mark.asyncio
async def test_read_tools_return_ids_and_data_for_the_delegated_user(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting,
    db_session: AsyncSession, fake_retriever: FakeRetriever,
) -> None:
    owner = await register_user("owner@example.com")
    meeting, segments = await seed_meeting(db_session, make_meeting, owner.id)
    headers = await delegated_headers(db_session, owner, meeting)
    fake_retriever.chunks = [
        RetrievedChunk(uuid.uuid4(), 0, "Speaker 1", 0.0, 10.0, "chunk text", [segments[0].id], 0.5)
    ]

    overview = (await client.get(f"{BASE}/{meeting.id}/overview", headers=headers)).json()
    assert overview["segments_count"] == 4 and overview["transcript_revision"] == 0
    assert {s["speaker_label"]: s["talk_time_seconds"] for s in overview["speakers"]} == {
        "Speaker 1": 20.0, "Speaker 2": 20.0,
    }

    found = (await client.post(f"{BASE}/{meeting.id}/find", headers=headers, json={"pattern": "gemany"})).json()
    assert [f["segment_id"] for f in found] == [str(s.id) for s in segments[:3]]
    sensitive = await client.post(
        f"{BASE}/{meeting.id}/find", headers=headers, json={"pattern": "gemany", "case_sensitive": True}
    )
    assert sensitive.json() == []

    window = (await client.get(f"{BASE}/{meeting.id}/segments?from_time=15&to_time=25", headers=headers)).json()
    assert [w["segment_id"] for w in window] == [str(segments[1].id), str(segments[2].id)]
    by_speaker = (await client.get(f"{BASE}/{meeting.id}/segments?speaker=Speaker 2&limit=1", headers=headers)).json()
    assert [w["segment_id"] for w in by_speaker] == [str(segments[2].id)]

    hits = (await client.post(f"{BASE}/{meeting.id}/search", headers=headers, json={"query": "gì", "k": 3})).json()
    assert hits[0]["text"] == "chunk text" and hits[0]["segment_ids"] == [str(segments[0].id)]
    summary = (await client.get(f"{BASE}/{meeting.id}/summary", headers=headers)).json()
    assert summary["summary_status"] == "ready" and summary["action_items"] == []


@pytest.mark.asyncio
async def test_proposals_are_stored_with_a_preview_and_change_nothing(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting,
    db_session: AsyncSession, upgrade_to_pro: UpgradeToPro,
) -> None:
    owner = await register_user("owner@example.com")
    await upgrade_to_pro(owner.id)
    meeting, segments = await seed_meeting(db_session, make_meeting, owner.id)
    headers = await delegated_headers(db_session, owner, meeting)

    response = await propose(client, meeting.id, headers, {
        "kind": "transcript_ops", "base_revision": 0,
        "operations": [{"op": "replace_text", "find": "Gemany", "replace": "Gemini"}],
    })

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "proposed" and body["base_revision"] == 0
    assert len(body["preview"]["changes"]) == 3
    assert body["payload"]["operations"][0]["op"] == "replace_text"
    contents = (await db_session.scalars(select(TranscriptSegmentModel.content))).all()
    assert not any("Gemini" in c for c in contents)
    assert await db_session.scalar(select(func.count()).select_from(TranscriptChangeSetModel)) == 0
    assert meeting.transcript_revision == 0


@pytest.mark.asyncio
async def test_proposals_are_validated_before_they_are_stored(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting,
    db_session: AsyncSession, upgrade_to_pro: UpgradeToPro,
) -> None:
    owner = await register_user("owner@example.com")
    await upgrade_to_pro(owner.id)
    meeting, segments = await seed_meeting(db_session, make_meeting, owner.id)
    headers = await delegated_headers(db_session, owner, meeting)
    op = [{"op": "update_text", "segment_id": str(segments[0].id), "new_text": "x"}]

    stale = await propose(client, meeting.id, headers, {"kind": "transcript_ops", "base_revision": 7, "operations": op})
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "TRANSCRIPT_REVISION_CONFLICT"
    invented = await propose(client, meeting.id, headers, {
        "kind": "transcript_ops", "base_revision": 0,
        "operations": [{"op": "delete_segments", "segment_ids": [str(uuid.uuid4())]}],
    })
    assert invented.status_code == 422 and invented.json()["error"]["code"] == "SEGMENT_NOT_FOUND"
    empty = await propose(client, meeting.id, headers, {"kind": "transcript_ops", "base_revision": 0})
    assert empty.status_code == 422
    too_many = await propose(client, meeting.id, headers, {
        "kind": "transcript_ops", "base_revision": 0, "operations": op * 201,
    })
    assert too_many.status_code == 422
    assert await db_session.scalar(select(func.count()).select_from(AgentActionModel)) == 0


@pytest.mark.asyncio
async def test_agent_writes_need_edit_rights_and_a_plan_with_agent_tools(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting,
    db_session: AsyncSession, upgrade_to_pro: UpgradeToPro,
) -> None:
    owner = await register_user("owner@example.com")
    viewer = await register_user("viewer@example.com")
    await upgrade_to_pro(viewer.id)
    meeting, segments = await seed_meeting(db_session, make_meeting, owner.id)
    project = await client.post("/api/v1/projects", headers=owner.headers, json={"name": "P"})
    pid = project.json()["id"]
    await client.post(f"/api/v1/projects/{pid}/members", headers=owner.headers,
                      json={"email": viewer.email, "role": "viewer"})
    await client.post(f"/api/v1/projects/{pid}/meetings/{meeting.id}", headers=owner.headers)
    body = {"kind": "summary_regenerate", "base_revision": 0}

    viewer_headers = await delegated_headers(db_session, viewer, meeting)
    denied = await propose(client, meeting.id, viewer_headers, body)
    assert denied.status_code == 403 and denied.json()["error"]["code"] == "MEETING_FORBIDDEN"
    assert (await client.get(f"{BASE}/{meeting.id}/overview", headers=viewer_headers)).status_code == 200

    owner_headers = await delegated_headers(db_session, owner, meeting)
    free_plan = await propose(client, meeting.id, owner_headers, body)
    assert free_plan.status_code == 402 and free_plan.json()["error"]["code"] == "PLAN_FEATURE_REQUIRED"
    artifact = await client.post(
        f"{BASE}/{meeting.id}/artifacts", headers=owner_headers, json={"kind": "srt", "title": "t"}
    )
    assert artifact.status_code == 402


@pytest.mark.asyncio
async def test_the_agent_cannot_use_a_share_token_to_gain_access(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting,
    db_session: AsyncSession, upgrade_to_pro: UpgradeToPro,
) -> None:
    owner = await register_user("owner@example.com")
    stranger = await register_user("stranger@example.com")
    await upgrade_to_pro(stranger.id)
    meeting, _ = await seed_meeting(
        db_session, make_meeting, owner.id, share_token="editor-share-token-1234567", share_permission="editor"
    )
    headers = await delegated_headers(db_session, stranger, meeting)

    response = await client.get(f"{BASE}/{meeting.id}/overview?share=editor-share-token-1234567", headers=headers)
    assert response.status_code == 403
    assert settings.ai_service_token  # sanity: the service token itself is not the issue
