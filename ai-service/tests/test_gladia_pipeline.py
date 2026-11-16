import pytest
from app.pipelines.gladia import GladiaAudioPipeline


def test_parse_utterances_to_segments() -> None:
    """Verify that Gladia API v2 utterance payload is converted to standardized segments."""
    pipeline = GladiaAudioPipeline(api_key="test_key")

    mock_gladia_data = {
        "status": "done",
        "result": {
            "transcription": {
                "utterances": [
                    {
                        "id": 0,
                        "start": 0.0,
                        "end": 2.5,
                        "speaker": 1,
                        "text": "Chào mừng bạn đến với phiên họp.",
                        "confidence": 0.98,
                        "words": [
                            {"word": "Chào", "start": 0.0, "end": 0.4, "confidence": 0.99},
                            {"word": "mừng", "start": 0.5, "end": 0.9, "confidence": 0.98},
                        ],
                    },
                    {
                        "id": 1,
                        "start": 2.8,
                        "end": 5.2,
                        "speaker": 2,
                        "text": "Hôm nay chúng ta bàn về kiến trúc API-first.",
                        "confidence": 0.95,
                        "words": [
                            {"word": "Hôm", "start": 2.8, "end": 3.1, "confidence": 0.97},
                        ],
                    },
                ]
            }
        },
    }

    segments = pipeline.parse_utterances_to_segments(mock_gladia_data)

    assert len(segments) == 2

    seg1 = segments[0]
    assert seg1["speaker"] == "SPEAKER_01"
    assert seg1["start"] == 0.0
    assert seg1["end"] == 2.5
    assert seg1["start_ms"] == 0
    assert seg1["end_ms"] == 2500
    assert seg1["text"] == "Chào mừng bạn đến với phiên họp."
    assert len(seg1["words"]) == 2
    assert seg1["words"][0]["w"] == "Chào"
    assert seg1["words"][0]["s"] == 0
    assert seg1["words"][0]["e"] == 400

    seg2 = segments[1]
    assert seg2["speaker"] == "SPEAKER_02"
    assert seg2["text"] == "Hôm nay chúng ta bàn về kiến trúc API-first."


@pytest.mark.asyncio
async def test_process_audio_fallback_when_no_api_key() -> None:
    """Ensure graceful fallback occurs when Gladia API key is empty."""
    pipeline = GladiaAudioPipeline(api_key="")
    segments = await pipeline.process_audio(audio_path="dummy.wav")
    assert len(segments) >= 2
    assert "SPEAKER_00" in segments[0]["speaker"]
    assert "words" in segments[0]
    assert len(segments[0]["words"]) > 0
