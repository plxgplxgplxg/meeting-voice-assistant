import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utc_now
from app.models.billing import PlanConfigModel
from app.models.summary import ActionItemModel, SummaryModel
from app.models.transcript import TranscriptSegmentModel
from app.services.billing.subscription_service import SubscriptionService
from tests.conftest import MakeMeeting, RegisterUser


async def seed_content(db_session: AsyncSession, meeting_id) -> None:
    db_session.add_all([
        TranscriptSegmentModel(
            meeting_id=meeting_id, speaker_label="Speaker 1", start_time=0.0, end_time=12.5,
            content="Xin chào mọi người, hôm nay chúng ta họp tổng kết quý 1.", sequence_order=1,
        ),
        TranscriptSegmentModel(
            meeting_id=meeting_id, speaker_label="Speaker 2", start_time=13.0, end_time=25.0,
            content="Mục tiêu doanh số đã đạt 120% kế hoạch đề ra.", sequence_order=2,
        ),
        SummaryModel(
            meeting_id=meeting_id,
            executive_summary="Cuộc họp tổng kết kết quả kinh doanh quý 1 vượt chỉ tiêu.",
            key_points=["Doanh số đạt 120% kế hoạch"],
        ),
        ActionItemModel(
            meeting_id=meeting_id, description="Chuẩn bị báo cáo tài chính chi tiết",
            assignee="Speaker 2", status="pending",
        ),
    ])
    await db_session.flush()


@pytest.mark.asyncio
async def test_free_plan_exports_txt_and_json_only(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting,
    db_session: AsyncSession,
) -> None:
    """Free owners can export txt/json, while srt, vtt and docx need an upgrade."""
    owner = await register_user("owner@example.com")
    meeting = await make_meeting(owner.id)
    await seed_content(db_session, meeting.id)

    txt = await client.get(f"/api/v1/meetings/{meeting.id}/exports/txt", headers=owner.headers)
    assert txt.status_code == 200
    assert "BIÊN BẢN CUỘC HỌP" in txt.text and "Xin chào mọi người" in txt.text

    json_res = await client.get(f"/api/v1/meetings/{meeting.id}/exports/json", headers=owner.headers)
    assert json_res.status_code == 200
    assert len(json_res.json()["transcript"]) == 2

    for blocked in ("docx", "srt", "vtt"):
        res = await client.get(
            f"/api/v1/meetings/{meeting.id}/exports/{blocked}", headers=owner.headers
        )
        assert res.status_code == 402, blocked
        assert res.json()["error"]["code"] == "PLAN_FEATURE_REQUIRED"


@pytest.mark.asyncio
async def test_pro_plan_exports_every_format(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting,
    db_session: AsyncSession,
) -> None:
    """A Pro owner can export all formats, including via a share link guest."""
    owner = await register_user("owner@example.com")
    pro = await db_session.scalar(select(PlanConfigModel).where(PlanConfigModel.slug == "pro"))
    await SubscriptionService(db_session).activate_paid_plan(owner.id, pro, utc_now())
    meeting = await make_meeting(owner.id, share_token="guest-share-token-0123456789")
    await seed_content(db_session, meeting.id)

    srt = await client.get(f"/api/v1/meetings/{meeting.id}/exports/srt", headers=owner.headers)
    assert "00:00:00,000 --> 00:00:12,500" in srt.text
    assert "[Speaker 1] Xin chào mọi người" in srt.text

    vtt = await client.get(f"/api/v1/meetings/{meeting.id}/exports/vtt", headers=owner.headers)
    assert "WEBVTT" in vtt.text and "00:00:00.000 --> 00:00:12.500" in vtt.text

    docx = await client.get(f"/api/v1/meetings/{meeting.id}/exports/docx", headers=owner.headers)
    assert docx.status_code == 200
    assert docx.content[:4] == b"PK\x03\x04"

    guest_docx = await client.get(
        f"/api/v1/meetings/{meeting.id}/exports/docx?share=guest-share-token-0123456789"
    )
    assert guest_docx.status_code == 200


@pytest.mark.asyncio
async def test_unsupported_export_format_is_rejected(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting
) -> None:
    """An unknown format yields a validation error, not a server error."""
    owner = await register_user("owner@example.com")
    meeting = await make_meeting(owner.id)
    res = await client.get(f"/api/v1/meetings/{meeting.id}/exports/pdf", headers=owner.headers)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "UNSUPPORTED_EXPORT_FORMAT"


def test_registry_is_open_for_new_formats_without_editing_existing_code() -> None:
    """A new renderer plugs in by registration alone and is looked up case-insensitively."""
    from app.services.export.registry import ExportRegistry, build_default_registry

    class MarkdownRenderer:
        format = "md"
        media_type = "text/markdown"
        extension = "md"

        def render(self, doc) -> bytes:
            return f"# {doc.title}".encode()

    registry = build_default_registry()
    assert set(registry.formats) == {"txt", "docx", "srt", "vtt", "json"}
    registry.register(MarkdownRenderer())
    assert registry.get("MD").extension == "md"
    assert ExportRegistry().formats == ()
