import httpx
import pytest

from app.core.errors import ProviderNotConfiguredError
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
async def test_submit_without_api_key_raises_instead_of_inventing_a_transcript() -> None:
    """Without a Gladia key the pipeline fails explicitly and returns no demo segments."""
    pipeline = GladiaAudioPipeline(api_key="")
    with pytest.raises(ProviderNotConfiguredError) as exc:
        await pipeline.submit(audio_path="dummy.wav")
    assert exc.value.message == "ASR provider not configured"
    with pytest.raises(ProviderNotConfiguredError):
        await pipeline.get_result("job-1")


@pytest.mark.asyncio
async def test_submit_uploads_then_creates_job_and_returns_its_id(tmp_path) -> None:
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"RIFF....WAVE")
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        if request.url.path == "/v2/upload":
            return httpx.Response(200, json={"audio_url": "https://files/a.wav"})
        return httpx.Response(201, json={"id": "job-42", "result_url": "ignored"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        pipeline = GladiaAudioPipeline(api_key="k", base_url="https://gladia.test", client=client)
        job_id = await pipeline.submit(str(audio))

    assert job_id == "job-42"
    assert calls == ["POST /v2/upload", "POST /v2/pre-recorded"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("body", "expected_status"),
    [
        ({"status": "queued"}, "processing"),
        ({"status": "processing"}, "processing"),
        ({"status": "error", "error": "bad audio"}, "error"),
        (
            {"status": "done", "result": {"transcription": {"utterances": [{"id": 0, "speaker": 0, "start": 0, "end": 1, "text": "hi"}]}}},
            "done",
        ),
    ],
)
async def test_get_result_maps_gladia_status_without_waiting(body, expected_status) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/pre-recorded/job-42"
        return httpx.Response(200, json=body)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        pipeline = GladiaAudioPipeline(api_key="k", base_url="https://gladia.test", client=client)
        result = await pipeline.get_result("job-42")

    assert result.status == expected_status
    if expected_status == "done":
        assert result.segments[0]["text"] == "hi"
    if expected_status == "error":
        assert result.error == "bad audio"
