import io

import pytest
from docx import Document
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.export.markdown_docx import markdown_to_docx
from tests.agent_helpers import seed_meeting
from tests.conftest import MakeMeeting, RegisterUser, UpgradeToPro


def read_docx(data: bytes) -> list[str]:
    document = Document(io.BytesIO(data))
    texts = [p.text for p in document.paragraphs]
    for table in document.tables:
        texts.extend(cell.text for row in table.rows for cell in row.cells)
    return texts


def test_markdown_converter_handles_headings_lists_and_bold_and_never_executes_markup() -> None:
    data = markdown_to_docx("Biên bản", "# Mục 1\n- ý một\n- **ý hai** quan trọng\n1. bước\nĐoạn <script>alert(1)</script>")
    document = Document(io.BytesIO(data))
    styles = [(p.style.name, p.text) for p in document.paragraphs]

    assert ("Title", "Biên bản") in styles
    assert ("Heading 1", "Mục 1") in styles
    assert ("List Bullet", "ý một") in styles
    bold = next(p for p in document.paragraphs if p.text.startswith("ý hai"))
    assert bold.runs[0].bold and bold.text == "ý hai quan trọng"
    assert ("List Number", "bước") in styles
    assert any("<script>alert(1)</script>" in text for _, text in styles)


@pytest.mark.asyncio
async def test_pro_user_generates_lists_downloads_and_deletes_artifacts(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting,
    db_session: AsyncSession, upgrade_to_pro: UpgradeToPro,
) -> None:
    owner = await register_user("owner@example.com")
    await upgrade_to_pro(owner.id)
    meeting, _ = await seed_meeting(db_session, make_meeting, owner.id)
    base = f"/api/v1/meetings/{meeting.id}/artifacts"

    minutes = await client.post(base, headers=owner.headers, json={"kind": "minutes_docx", "title": "Biên bản họp"})
    assert minutes.status_code == 201, minutes.text
    assert minutes.json()["source_revision"] == 0 and minutes.json()["size_bytes"] > 1000

    written = await client.post(base, headers=owner.headers, json={
        "kind": "minutes_docx", "title": "Biên bản ngắn", "content_markdown": "# Quyết định\n- Dùng Gemini",
    })
    email = await client.post(base, headers=owner.headers, json={
        "kind": "email_draft", "title": "Email action items", "content_markdown": "Chào team,\n- Linh làm slide",
    })
    srt = await client.post(base, headers=owner.headers, json={"kind": "srt", "title": "Phụ đề"})
    assert [r.status_code for r in (written, email, srt)] == [201, 201, 201]

    listing = (await client.get(base, headers=owner.headers)).json()
    assert len(listing) == 4

    docx_download = await client.get(f"{base}/{minutes.json()['id']}/download", headers=owner.headers)
    assert docx_download.status_code == 200
    assert "wordprocessingml" in docx_download.headers["content-type"]
    assert any("Xin chào" in t for t in read_docx(docx_download.content))
    short = await client.get(f"{base}/{written.json()['id']}/download", headers=owner.headers)
    assert "Dùng Gemini" in read_docx(short.content)
    srt_download = await client.get(f"{base}/{srt.json()['id']}/download", headers=owner.headers)
    assert "00:00:00,000 --> 00:00:10,000" in srt_download.text

    deleted = await client.delete(f"{base}/{email.json()['id']}", headers=owner.headers)
    assert deleted.status_code == 204
    assert len((await client.get(base, headers=owner.headers)).json()) == 3
    assert (await client.get(f"{base}/{email.json()['id']}/download", headers=owner.headers)).status_code == 404


@pytest.mark.asyncio
async def test_artifact_inputs_are_validated(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting,
    db_session: AsyncSession, upgrade_to_pro: UpgradeToPro,
) -> None:
    owner = await register_user("owner@example.com")
    await upgrade_to_pro(owner.id)
    meeting, _ = await seed_meeting(db_session, make_meeting, owner.id)
    base = f"/api/v1/meetings/{meeting.id}/artifacts"

    missing = await client.post(base, headers=owner.headers, json={"kind": "email_draft", "title": "x"})
    assert missing.status_code == 422 and missing.json()["error"]["code"] == "ARTIFACT_CONTENT_REQUIRED"
    huge = await client.post(base, headers=owner.headers, json={
        "kind": "custom_md", "title": "x", "content_markdown": "a" * 200_001,
    })
    assert huge.status_code == 422 and huge.json()["error"]["code"] == "ARTIFACT_TOO_LARGE"
    unknown = await client.post(base, headers=owner.headers, json={"kind": "exe", "title": "x"})
    assert unknown.status_code == 422


@pytest.mark.asyncio
async def test_permissions_plan_gating_and_isolation(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting,
    db_session: AsyncSession, upgrade_to_pro: UpgradeToPro,
) -> None:
    owner = await register_user("owner@example.com")
    await upgrade_to_pro(owner.id)
    editor = await register_user("editor@example.com")
    await upgrade_to_pro(editor.id)
    free_user = await register_user("free@example.com")
    meeting, _ = await seed_meeting(
        db_session, make_meeting, owner.id, share_token="viewer-share-token-1234567", share_permission="viewer"
    )
    other_meeting, _ = await seed_meeting(db_session, make_meeting, owner.id)
    project = (await client.post("/api/v1/projects", headers=owner.headers, json={"name": "P"})).json()["id"]
    for user, role in ((editor, "editor"), (free_user, "viewer")):
        await client.post(f"/api/v1/projects/{project}/members", headers=owner.headers,
                          json={"email": user.email, "role": role})
    await client.post(f"/api/v1/projects/{project}/meetings/{meeting.id}", headers=owner.headers)
    base = f"/api/v1/meetings/{meeting.id}/artifacts"
    created = (await client.post(base, headers=owner.headers, json={"kind": "srt", "title": "S"})).json()

    # creating needs only VIEW access plus a plan with agent tools
    assert (await client.post(base, headers=editor.headers, json={"kind": "srt", "title": "E"})).status_code == 201
    free_attempt = await client.post(base, headers=free_user.headers, json={"kind": "srt", "title": "F"})
    assert free_attempt.status_code == 402 and free_attempt.json()["error"]["code"] == "PLAN_FEATURE_REQUIRED"
    # anyone who can view may list and download, including a share-link guest
    guest = "?share=viewer-share-token-1234567"
    assert (await client.get(f"{base}{guest}")).status_code == 200
    assert (await client.get(f"{base}/{created['id']}/download{guest}")).status_code == 200
    # deleting needs MANAGE: a project editor cannot, the creator can
    assert (await client.delete(f"{base}/{created['id']}", headers=editor.headers)).status_code == 403
    assert (await client.delete(f"{base}/{created['id']}{guest}")).status_code == 403
    # an artifact id from another meeting is not found
    foreign = f"/api/v1/meetings/{other_meeting.id}/artifacts/{created['id']}/download"
    assert (await client.get(foreign, headers=owner.headers)).status_code == 404
    assert (await client.delete(f"{base}/{created['id']}", headers=owner.headers)).status_code == 204
