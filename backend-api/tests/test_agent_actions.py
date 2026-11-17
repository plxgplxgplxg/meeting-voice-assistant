import uuid
from datetime import timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utc_now
from app.models.agent import AgentActionModel
from app.models.processing_job import ProcessingJobModel
from app.models.summary import ActionItemModel
from app.models.transcript_revision import TranscriptChangeSetModel
from tests.agent_helpers import delegated_headers, propose, seed_meeting
from tests.conftest import RegisterUser


@pytest_asyncio.fixture(loop_scope="function")
async def setup(client, register_user, make_meeting, db_session, upgrade_to_pro):
    owner = await register_user("owner@example.com")
    await upgrade_to_pro(owner.id)
    meeting, segments = await seed_meeting(db_session, make_meeting, owner.id)
    headers = await delegated_headers(db_session, owner, meeting)
    return owner, meeting, segments, headers


async def propose_replace(client, meeting, headers) -> str:
    response = await propose(client, meeting.id, headers, {
        "kind": "transcript_ops", "base_revision": 0,
        "operations": [{"op": "replace_text", "find": "Gemany", "replace": "Gemini"}],
    })
    return response.json()["id"]


async def transcript(client, meeting, owner) -> list[str]:
    response = await client.get(f"/api/v1/meetings/{meeting.id}/transcript", headers=owner.headers)
    return [s["content"] for s in response.json()]


def url(meeting, action_id: str, verb: str) -> str:
    return f"/api/v1/meetings/{meeting.id}/agent-actions/{action_id}:{verb}"


@pytest.mark.asyncio
async def test_approve_applies_through_the_command_layer_and_records_the_agent(
    client: AsyncClient, setup, db_session: AsyncSession
) -> None:
    owner, meeting, segments, headers = setup
    action_id = await propose_replace(client, meeting, headers)

    approved = await client.post(url(meeting, action_id, "approve"), headers=owner.headers)

    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["status"] == "applied" and body["result"]["revision"] == 1
    assert body["change_set_id"] and body["decided_at"]
    assert await transcript(client, meeting, owner) == [
        "Xin chào, hôm nay họp về Gemini.", "Gemini là nhà cung cấp mô hình.",
        "Đồng ý, ta dùng Gemini cho bản demo.", "Hẹn gặp lại.",
    ]
    change_set = await db_session.get(TranscriptChangeSetModel, uuid.UUID(body["change_set_id"]))
    assert change_set.actor_type == "agent" and change_set.actor_user_id == owner.id
    assert (meeting.summary_status, meeting.index_status) == ("stale", "stale")
    jobs = (await db_session.scalars(select(ProcessingJobModel))).all()
    assert [j.kind for j in jobs] == ["index"]


@pytest.mark.asyncio
async def test_approved_agent_edit_can_be_reverted_to_the_exact_previous_text(
    client: AsyncClient, setup
) -> None:
    owner, meeting, _, headers = setup
    original = await transcript(client, meeting, owner)
    action_id = await propose_replace(client, meeting, headers)
    approved = (await client.post(url(meeting, action_id, "approve"), headers=owner.headers)).json()
    assert await transcript(client, meeting, owner) != original

    reverted = await client.post(
        f"/api/v1/meetings/{meeting.id}/transcript/change-sets/{approved['change_set_id']}/revert",
        headers=owner.headers,
    )

    assert reverted.status_code == 200
    assert await transcript(client, meeting, owner) == original


@pytest.mark.asyncio
async def test_stale_proposals_return_409_and_are_marked_expired(client: AsyncClient, setup) -> None:
    owner, meeting, segments, headers = setup
    action_id = await propose_replace(client, meeting, headers)
    manual = await client.patch(
        f"/api/v1/meetings/{meeting.id}/transcript/segments/{segments[3].id}",
        headers=owner.headers, json={"content": "Hẹn gặp lại sau."},
    )
    assert manual.status_code == 200

    stale = await client.post(url(meeting, action_id, "approve"), headers=owner.headers)

    assert stale.status_code == 409 and stale.json()["error"]["code"] == "PROPOSAL_STALE"
    listed = (await client.get(f"/api/v1/meetings/{meeting.id}/agent-actions", headers=owner.headers)).json()
    assert listed[0]["status"] == "expired"
    assert not any("Gemini" in c for c in await transcript(client, meeting, owner))


@pytest.mark.asyncio
async def test_proposals_expire_after_thirty_minutes(
    client: AsyncClient, setup, db_session: AsyncSession
) -> None:
    owner, meeting, _, headers = setup
    action_id = await propose_replace(client, meeting, headers)
    action = await db_session.get(AgentActionModel, uuid.UUID(action_id))
    action.created_at = utc_now() - timedelta(minutes=31)
    await db_session.flush()

    response = await client.post(url(meeting, action_id, "approve"), headers=owner.headers)

    assert response.status_code == 409 and response.json()["error"]["code"] == "PROPOSAL_EXPIRED"
    assert action.status == "expired"


@pytest.mark.asyncio
async def test_reject_discards_and_a_decision_is_final(client: AsyncClient, setup) -> None:
    owner, meeting, _, headers = setup
    action_id = await propose_replace(client, meeting, headers)

    rejected = await client.post(url(meeting, action_id, "reject"), headers=owner.headers)
    assert rejected.status_code == 200 and rejected.json()["status"] == "rejected"
    for verb in ("approve", "reject"):
        again = await client.post(url(meeting, action_id, verb), headers=owner.headers)
        assert again.status_code == 409 and again.json()["error"]["code"] == "ALREADY_DECIDED"
    assert not any("Gemini" in c for c in await transcript(client, meeting, owner))


@pytest.mark.asyncio
async def test_only_the_owner_of_a_proposal_can_decide_it(
    client: AsyncClient, setup, register_user: RegisterUser
) -> None:
    owner, meeting, _, headers = setup
    action_id = await propose_replace(client, meeting, headers)
    project = (await client.post("/api/v1/projects", headers=owner.headers, json={"name": "P"})).json()["id"]
    colleague = await register_user("colleague@example.com")
    await client.post(f"/api/v1/projects/{project}/members", headers=owner.headers,
                      json={"email": colleague.email, "role": "editor"})
    await client.post(f"/api/v1/projects/{project}/meetings/{meeting.id}", headers=owner.headers)
    stranger = await register_user("stranger@example.com")

    for user, expected in ((colleague, 403), (stranger, 403)):
        response = await client.post(url(meeting, action_id, "approve"), headers=user.headers)
        assert response.status_code == expected
    assert (await client.post(url(meeting, action_id, "approve"))).status_code == 401


@pytest.mark.asyncio
async def test_user_can_edit_the_operations_before_approving(client: AsyncClient, setup) -> None:
    owner, meeting, segments, headers = setup
    action_id = await propose_replace(client, meeting, headers)

    approved = await client.post(
        url(meeting, action_id, "approve"), headers=owner.headers,
        json={"operations": [{"op": "replace_text", "find": "Gemany", "replace": "Gemini Pro",
                              "scope": "segments", "segment_ids": [str(segments[0].id)]}]},
    )

    assert approved.status_code == 200
    contents = await transcript(client, meeting, owner)
    assert contents[0].endswith("Gemini Pro.") and "Gemany" in contents[1]


@pytest.mark.asyncio
async def test_action_item_proposals_create_user_owned_items_that_survive_regeneration(
    client: AsyncClient, setup, db_session: AsyncSession
) -> None:
    owner, meeting, _, headers = setup
    proposed = await propose(client, meeting.id, headers, {
        "kind": "action_item_ops", "base_revision": 0,
        "action_item_operations": [{"op": "create", "description": "Linh hoàn thành slide trước thứ 6", "assignee": "Linh"}],
    })
    assert proposed.status_code == 201 and proposed.json()["preview"]["changes"][0]["op"] == "create"
    assert (await db_session.scalars(select(ActionItemModel))).all() == []

    approved = await client.post(url(meeting, proposed.json()["id"], "approve"), headers=owner.headers)

    assert approved.status_code == 200
    item = (await db_session.scalars(select(ActionItemModel))).one()
    assert (item.description, item.assignee, item.source, item.status) == (
        "Linh hoàn thành slide trước thứ 6", "Linh", "user", "pending",
    )
    items = (await client.get(f"/api/v1/meetings/{meeting.id}/action-items", headers=owner.headers)).json()
    assert [i["description"] for i in items] == ["Linh hoàn thành slide trước thứ 6"]


@pytest.mark.asyncio
async def test_action_item_updates_validate_ids(client: AsyncClient, setup) -> None:
    owner, meeting, _, headers = setup
    response = await propose(client, meeting.id, headers, {
        "kind": "action_item_ops", "base_revision": 0,
        "action_item_operations": [{"op": "delete", "action_item_id": "00000000-0000-0000-0000-000000000001"}],
    })
    assert response.status_code == 422 and response.json()["error"]["code"] == "ACTION_ITEM_NOT_FOUND"


@pytest.mark.asyncio
async def test_summary_regeneration_proposal_queues_a_job_only_after_approval(
    client: AsyncClient, setup, db_session: AsyncSession
) -> None:
    owner, meeting, _, headers = setup
    proposed = await propose(client, meeting.id, headers, {"kind": "summary_regenerate", "base_revision": 0})
    assert proposed.status_code == 201
    assert (await db_session.scalars(select(ProcessingJobModel))).all() == []

    approved = await client.post(url(meeting, proposed.json()["id"], "approve"), headers=owner.headers)

    assert approved.status_code == 200 and approved.json()["result"] == {"summary_status": "pending"}
    assert [j.kind for j in (await db_session.scalars(select(ProcessingJobModel))).all()] == ["summarize"]


@pytest.mark.asyncio
async def test_each_user_only_sees_their_own_proposals(
    client: AsyncClient, setup, register_user: RegisterUser
) -> None:
    owner, meeting, _, headers = setup
    await propose_replace(client, meeting, headers)
    other = await register_user("other@example.com")

    mine = (await client.get(f"/api/v1/meetings/{meeting.id}/agent-actions?status=proposed", headers=owner.headers)).json()
    theirs = await client.get(f"/api/v1/meetings/{meeting.id}/agent-actions", headers=other.headers)

    assert len(mine) == 1
    assert theirs.status_code == 403
