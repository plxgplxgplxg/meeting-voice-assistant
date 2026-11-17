import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest
from httpx import AsyncClient

from app.domain.enums import Permission
from tests.conftest import Account, MakeMeeting, RegisterUser

SHARE_TOKEN = "share-token-for-tests-0123456789"


@dataclass(frozen=True)
class Route:
    """A meeting-scoped route and the permission it demands."""

    method: str
    path: str
    permission: Permission
    body: dict[str, Any] | None = field(default=None, hash=False, compare=False)


FAKE_ID = str(uuid.uuid4())

ROUTES = [
    Route("GET", "/api/v1/meetings/{m}", Permission.VIEW),
    Route("GET", "/api/v1/meetings/{m}/transcript", Permission.VIEW),
    Route("GET", "/api/v1/transcripts/{m}", Permission.VIEW),
    Route("GET", "/api/v1/meetings/{m}/summary", Permission.VIEW),
    Route("GET", "/api/v1/summaries/{m}", Permission.VIEW),
    Route("GET", "/api/v1/meetings/{m}/action-items", Permission.VIEW),
    Route("GET", "/api/v1/summaries/{m}/action-items", Permission.VIEW),
    Route("GET", "/api/v1/meetings/{m}/chat/messages", Permission.VIEW),
    Route("GET", "/api/v1/chat/{m}/messages", Permission.VIEW),
    Route("POST", "/api/v1/meetings/{m}/chat", Permission.VIEW, {"query": "What was decided?"}),
    Route("POST", "/api/v1/chat/{m}", Permission.VIEW, {"query": "What was decided?"}),
    Route("GET", "/api/v1/meetings/{m}/exports/txt", Permission.VIEW),
    Route("GET", "/api/v1/exports/{m}/txt", Permission.VIEW),
    Route("GET", "/api/v1/meetings/{m}/audio/playback", Permission.VIEW),
    Route("GET", "/api/v1/audio/{m}/playback", Permission.VIEW),
    Route("GET", "/api/v1/meetings/{m}/audio/stream", Permission.VIEW),
    Route("PATCH", "/api/v1/meetings/{m}", Permission.EDIT, {"title": "Renamed"}),
    Route(
        "PATCH",
        f"/api/v1/meetings/{{m}}/transcript/segments/{FAKE_ID}",
        Permission.EDIT,
        {"content": "fixed"},
    ),
    Route(
        "POST",
        "/api/v1/meetings/{m}/transcript/rename-speaker",
        Permission.EDIT,
        {"old_speaker_label": "A", "new_speaker_label": "B"},
    ),
    Route(
        "POST",
        "/api/v1/transcripts/{m}/rename-speaker",
        Permission.EDIT,
        {"old_speaker_label": "A", "new_speaker_label": "B"},
    ),
    Route(
        "POST",
        "/api/v1/meetings/{m}/transcript/delete-segments",
        Permission.EDIT,
        {"segment_ids": [FAKE_ID]},
    ),
    Route(
        "POST",
        "/api/v1/transcripts/{m}/delete-segments",
        Permission.EDIT,
        {"segment_ids": [FAKE_ID]},
    ),
    Route(
        "PATCH",
        f"/api/v1/meetings/{{m}}/action-items/{FAKE_ID}",
        Permission.EDIT,
        {"status": "completed"},
    ),
    Route("POST", "/api/v1/meetings/{m}/reprocess", Permission.EDIT),
    Route("POST", "/api/v1/meetings/{m}/reindex", Permission.EDIT),
    Route("POST", "/api/v1/meetings/{m}/summary:regenerate", Permission.EDIT),
    Route("GET", "/api/v1/meetings/{m}/audio/stream-url", Permission.VIEW),
    Route("GET", "/api/v1/meetings/{m}/transcript/change-sets", Permission.VIEW),
    Route("GET", f"/api/v1/meetings/{{m}}/transcript/change-sets/{FAKE_ID}", Permission.VIEW),
    Route(
        "POST",
        "/api/v1/meetings/{m}/transcript/operations",
        Permission.EDIT,
        {"operations": [{"op": "rename_speaker", "old_label": "A", "new_label": "B"}]},
    ),
    Route(
        "POST",
        "/api/v1/meetings/{m}/transcript/operations:preview",
        Permission.EDIT,
        {"operations": [{"op": "rename_speaker", "old_label": "A", "new_label": "B"}]},
    ),
    Route(
        "POST", f"/api/v1/meetings/{{m}}/transcript/change-sets/{FAKE_ID}/revert", Permission.EDIT
    ),
    Route("POST", "/api/v1/meetings/{m}/share?permission=viewer", Permission.MANAGE),
    Route("DELETE", "/api/v1/meetings/{m}", Permission.MANAGE),
]

ROLE_GRANTS: dict[str, Permission | None] = {
    "anonymous": None,
    "other_user": None,
    "project_viewer": Permission.VIEW,
    "project_editor": Permission.EDIT,
    "share_viewer": Permission.VIEW,
    "share_editor": Permission.EDIT,
    "creator": Permission.MANAGE,
}
RANK = {Permission.VIEW: 1, Permission.EDIT: 2, Permission.MANAGE: 3}


async def build_world(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting, role: str
) -> tuple[str, dict[str, str], str]:
    """Create the meeting, project and users needed for ``role``.

    Returns:
        Tuple of meeting id, request headers for the role, and query suffix for share tokens.
    """
    creator = await register_user("creator@example.com")
    share_permission = "editor" if role == "share_editor" else "viewer"
    meeting = await make_meeting(
        creator.id, share_token=SHARE_TOKEN, share_permission=share_permission
    )

    users: dict[str, Account] = {
        "other_user": await register_user("other@example.com"),
        "project_viewer": await register_user("viewer@example.com"),
        "project_editor": await register_user("editor@example.com"),
        "creator": creator,
    }

    project = await client.post(
        "/api/v1/projects", headers=creator.headers, json={"name": "Workspace"}
    )
    project_id = project.json()["id"]
    for key, project_role in (("project_viewer", "viewer"), ("project_editor", "editor")):
        member = await client.post(
            f"/api/v1/projects/{project_id}/members",
            headers=creator.headers,
            json={"email": users[key].email, "role": project_role},
        )
        assert member.status_code == 201, member.text
    link = await client.post(
        f"/api/v1/projects/{project_id}/meetings/{meeting.id}", headers=creator.headers
    )
    assert link.status_code == 200, link.text

    headers = users[role].headers if role in users else {}
    query = f"share={SHARE_TOKEN}" if role.startswith("share_") else ""
    return str(meeting.id), headers, query


@pytest.mark.asyncio
@pytest.mark.parametrize("role", list(ROLE_GRANTS))
@pytest.mark.parametrize("route", ROUTES, ids=lambda r: f"{r.method} {r.path}")
async def test_route_authorization_matrix(
    client: AsyncClient,
    register_user: RegisterUser,
    make_meeting: MakeMeeting,
    route: Route,
    role: str,
) -> None:
    """Every meeting-scoped route denies actors below the required permission."""
    meeting_id, headers, share_query = await build_world(
        client, register_user, make_meeting, role
    )
    path = route.path.format(m=meeting_id)
    if share_query:
        path += ("&" if "?" in path else "?") + share_query

    response = await client.request(route.method, path, headers=headers, json=route.body)

    granted = ROLE_GRANTS[role]
    allowed = granted is not None and RANK[granted] >= RANK[route.permission]
    if allowed:
        assert response.status_code not in (401, 403), response.text
    else:
        assert response.status_code == 403, response.text
        assert response.json()["error"]["code"] == "MEETING_FORBIDDEN"


@pytest.mark.asyncio
async def test_deleted_meeting_is_not_found_for_everyone(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting
) -> None:
    """Soft-deleted meetings return 404 even to the creator."""
    creator = await register_user("creator@example.com")
    meeting = await make_meeting(creator.id)
    delete = await client.delete(f"/api/v1/meetings/{meeting.id}", headers=creator.headers)
    assert delete.status_code == 204

    response = await client.get(f"/api/v1/meetings/{meeting.id}", headers=creator.headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MEETING_NOT_FOUND"


@pytest.mark.asyncio
async def test_share_token_comparison_rejects_wrong_token(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting
) -> None:
    """A wrong share token grants nothing."""
    creator = await register_user("creator@example.com")
    meeting = await make_meeting(creator.id, share_token=SHARE_TOKEN)
    response = await client.get(f"/api/v1/meetings/{meeting.id}?share=wrong-token")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_legacy_meeting_without_creator_can_never_be_managed(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting
) -> None:
    """Rows with created_by NULL are deletable by nobody."""
    user = await register_user("someone@example.com")
    meeting = await make_meeting(None)
    response = await client.delete(f"/api/v1/meetings/{meeting.id}", headers=user.headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_legacy_segment_route_checks_the_owning_meeting(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting, db_session
) -> None:
    """Editing a segment through the old path requires EDIT on the segment's meeting."""
    from app.models.transcript import TranscriptSegmentModel

    owner = await register_user("owner@example.com")
    intruder = await register_user("intruder@example.com")
    meeting = await make_meeting(owner.id)
    segment = TranscriptSegmentModel(
        meeting_id=meeting.id,
        speaker_label="A",
        start_time=0,
        end_time=1,
        content="original",
        sequence_order=1,
    )
    db_session.add(segment)
    await db_session.flush()

    denied = await client.patch(
        f"/api/v1/transcripts/segments/{segment.id}",
        headers=intruder.headers,
        json={"content": "hijacked"},
    )
    assert denied.status_code == 403

    allowed = await client.patch(
        f"/api/v1/transcripts/segments/{segment.id}",
        headers=owner.headers,
        json={"content": "corrected"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["content"] == "corrected"

    cross_meeting = await make_meeting(owner.id, title="Other meeting")
    wrong_scope = await client.patch(
        f"/api/v1/meetings/{cross_meeting.id}/transcript/segments/{segment.id}",
        headers=owner.headers,
        json={"content": "x"},
    )
    assert wrong_scope.status_code == 404
