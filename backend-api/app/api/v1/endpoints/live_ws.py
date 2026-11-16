import json
import uuid
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.database import async_session_factory
from app.models.meeting import MeetingModel
from app.models.transcript import TranscriptSegmentModel

router = APIRouter(tags=["Live WebSocket"])


@router.websocket("/live/ws")
async def live_audio_transcription_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint receiving live audio chunks and streaming back interim transcripts.

    Client protocol:
    - Message 1: {"type": "start", "title": "Optional Title"} -> Responds with {"type": "started", "meeting_id": "..."}
    - Subsequent messages: binary audio chunk or JSON {"type": "audio_chunk", "data": "..."} -> Broadcasts {"type": "transcript_draft", ...}
    - Final message: {"type": "end"} -> Finalizes meeting and returns {"type": "ended"}
    """
    await websocket.accept()
    meeting_id: uuid.UUID | None = None
    sequence_order = 0

    try:
        while True:
            message = await websocket.receive()
            text_data = message.get("text")
            bytes_data = message.get("bytes")

            if text_data:
                try:
                    payload = json.loads(text_data)
                except json.JSONDecodeError:
                    continue

                msg_type = payload.get("type")

                if msg_type == "start":
                    title = payload.get("title") or f"Cuộc Họp Trực Tiếp - {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}"
                    async with async_session_factory() as session:
                        meeting = MeetingModel(
                            title=title,
                            status="recording",
                        )
                        session.add(meeting)
                        await session.commit()
                        meeting_id = meeting.id

                    await websocket.send_json({
                        "type": "started",
                        "meeting_id": str(meeting_id),
                        "status": "recording",
                    })

                elif msg_type == "end":
                    if meeting_id:
                        async with async_session_factory() as session:
                            meeting = await session.get(MeetingModel, meeting_id)
                            if meeting:
                                meeting.status = "completed"
                                session.add(meeting)
                                await session.commit()

                    await websocket.send_json({
                        "type": "ended",
                        "meeting_id": str(meeting_id) if meeting_id else None,
                        "status": "completed",
                    })
                    break

            elif bytes_data and meeting_id:
                # Simulated live VAD & ASR turn reception
                sequence_order += 1
                start_sec = (sequence_order - 1) * 3.0
                end_sec = sequence_order * 3.0
                content = f"Nội dung nhận diện trực tiếp phân đoạn #{sequence_order}."

                async with async_session_factory() as session:
                    segment = TranscriptSegmentModel(
                        meeting_id=meeting_id,
                        speaker_label="Speaker 1",
                        start_time=start_sec,
                        end_time=end_sec,
                        content=content,
                        sequence_order=sequence_order,
                    )
                    session.add(segment)
                    await session.commit()

                await websocket.send_json({
                    "type": "transcript_segment",
                    "meeting_id": str(meeting_id),
                    "segment": {
                        "speaker_label": "Speaker 1",
                        "start_time": start_sec,
                        "end_time": end_sec,
                        "content": content,
                        "sequence_order": sequence_order,
                    },
                })

    except WebSocketDisconnect:
        pass
    except Exception:
        await websocket.close()
