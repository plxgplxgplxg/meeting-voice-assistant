import pytest
from httpx import AsyncClient

from tests.conftest import MakeMeeting, RegisterUser


@pytest.mark.asyncio
async def test_project_editor_cannot_link_a_meeting_they_cannot_access(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting
) -> None:
    """Linking requires EDIT on the meeting, closing the privilege escalation path."""
    victim = await register_user("victim@example.com")
    attacker = await register_user("attacker@example.com")
    secret_meeting = await make_meeting(victim.id, title="Board meeting")

    project = await client.post(
        "/api/v1/projects", headers=attacker.headers, json={"name": "Attacker workspace"}
    )
    project_id = project.json()["id"]

    link = await client.post(
        f"/api/v1/projects/{project_id}/meetings/{secret_meeting.id}", headers=attacker.headers
    )
    assert link.status_code == 403

    read = await client.get(f"/api/v1/meetings/{secret_meeting.id}", headers=attacker.headers)
    assert read.status_code == 403


@pytest.mark.asyncio
async def test_owner_can_link_own_meeting_and_list_is_scoped(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting
) -> None:
    """Owners link their meetings; listing never returns other users' meetings."""
    owner = await register_user("owner@example.com")
    other = await register_user("other@example.com")
    mine = await make_meeting(owner.id, title="Mine")
    await make_meeting(other.id, title="Theirs")
    await make_meeting(None, title="Legacy orphan")

    project = await client.post("/api/v1/projects", headers=owner.headers, json={"name": "P"})
    link = await client.post(
        f"/api/v1/projects/{project.json()['id']}/meetings/{mine.id}", headers=owner.headers
    )
    assert link.status_code == 200

    listing = await client.get("/api/v1/meetings", headers=owner.headers)
    assert [m["title"] for m in listing.json()] == ["Mine"]
    assert (await client.get("/api/v1/meetings")).status_code == 401


@pytest.mark.asyncio
async def test_meeting_creation_requires_authentication_and_status_is_not_client_settable(
    client: AsyncClient, register_user: RegisterUser
) -> None:
    """Anonymous creation is refused and PATCH cannot change the processing status."""
    assert (await client.post("/api/v1/meetings", json={"title": "x"})).status_code == 401

    user = await register_user("u@example.com")
    created = await client.post("/api/v1/meetings", headers=user.headers, json={"title": "Plan"})
    assert created.status_code == 201
    assert created.json()["status"] == "draft"

    patched = await client.patch(
        f"/api/v1/meetings/{created.json()['id']}",
        headers=user.headers,
        json={"title": "Plan v2", "status": "ready"},
    )
    assert patched.status_code == 200
    assert patched.json()["title"] == "Plan v2"
    assert patched.json()["status"] == "draft"
