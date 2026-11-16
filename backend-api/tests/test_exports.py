import uuid
from datetime import datetime
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meeting import MeetingModel
from app.models.summary import ActionItemModel, SummaryModel
from app.models.transcript import TranscriptSegmentModel


@pytest.mark.asyncio
async def test_meeting_exports(client: AsyncClient, db_session: AsyncSession) -> None:
    """Test DOCX, TXT, SRT, VTT, and JSON export formats for a meeting.

    Args:
        client: AsyncClient for API endpoints.
        db_session: Database session fixture to seed meeting data.
    """
    # 1. Create a meeting with segments and summary
    meeting_id = uuid.uuid4()
    meeting = MeetingModel(
        id=meeting_id,
        title="Cuộc Họp Đánh Giá Quý 1",
        status="completed",
        duration_seconds=125.5,
        created_at=datetime.utcnow(),
    )
    db_session.add(meeting)

    seg1 = TranscriptSegmentModel(
        meeting_id=meeting_id,
        speaker_label="Speaker 1",
        start_time=0.0,
        end_time=12.5,
        content="Xin chào mọi người, hôm nay chúng ta họp tổng kết quý 1.",
        sequence_order=0,
    )
    seg2 = TranscriptSegmentModel(
        meeting_id=meeting_id,
        speaker_label="Speaker 2",
        start_time=13.0,
        end_time=25.0,
        content="Mục tiêu doanh số đã đạt 120% kế hoạch đề ra.",
        sequence_order=1,
    )
    db_session.add_all([seg1, seg2])

    summary = SummaryModel(
        meeting_id=meeting_id,
        executive_summary="Cuộc họp tổng kết kết quả kinh doanh quý 1 vượt chỉ tiêu.",
        key_points=["Doanh số đạt 120% kế hoạch", "Đội ngũ hoàn thành đúng hạn"],
    )
    db_session.add(summary)

    action = ActionItemModel(
        meeting_id=meeting_id,
        description="Chuẩn bị báo cáo tài chính chi tiết",
        assignee="Speaker 2",
        status="pending",
    )
    db_session.add(action)
    await db_session.commit()

    # 2. Test TXT export
    txt_res = await client.get(f"/api/v1/meetings/{meeting_id}/export?type=txt")
    assert txt_res.status_code == 200
    assert "text/plain" in txt_res.headers["content-type"]
    assert "BIÊN BẢN CUỘC HỌP" in txt_res.text
    assert "Xin chào mọi người" in txt_res.text

    # 3. Test SRT export
    srt_res = await client.get(f"/api/v1/meetings/{meeting_id}/export?type=srt")
    assert srt_res.status_code == 200
    assert "00:00:00,000 --> 00:00:12,500" in srt_res.text
    assert "[Speaker 1] Xin chào mọi người" in srt_res.text

    # 4. Test VTT export
    vtt_res = await client.get(f"/api/v1/meetings/{meeting_id}/export?type=vtt")
    assert vtt_res.status_code == 200
    assert "WEBVTT" in vtt_res.text
    assert "00:00:00.000 --> 00:00:12.500" in vtt_res.text

    # 5. Test JSON export
    json_res = await client.get(f"/api/v1/meetings/{meeting_id}/export?type=json")
    assert json_res.status_code == 200
    json_data = json_res.json()
    assert json_data["meeting_id"] == str(meeting_id)
    assert len(json_data["transcript"]) == 2
    assert json_data["summary"] is not None

    # 6. Test DOCX export
    docx_res = await client.get(f"/api/v1/meetings/{meeting_id}/export?type=docx")
    assert docx_res.status_code == 200
    assert "wordprocessingml.document" in docx_res.headers["content-type"]
    assert docx_res.content[:4] == b"PK\x03\x04"
