import uuid
from typing import Any

from app.pipelines.protocols import TranscriptionResult

DEMO_SEGMENTS: list[dict[str, Any]] = [
    {
        "segment_id": 0,
        "speaker": "SPEAKER_00",
        "start": 0.0,
        "end": 4.5,
        "start_ms": 0,
        "end_ms": 4500,
        "text": "Đây là dữ liệu mẫu: chúng ta bắt đầu phiên họp rà soát tiến độ.",
        "confidence": 1.0,
        "words": [],
    },
    {
        "segment_id": 1,
        "speaker": "SPEAKER_01",
        "start": 5.0,
        "end": 10.2,
        "start_ms": 5000,
        "end_ms": 10200,
        "text": "Đây là dữ liệu mẫu: backend đã chuyển sang kiến trúc API-first.",
        "confidence": 1.0,
        "words": [],
    },
]


class FakeAudioProcessor:
    """Audio processor returning fixed demo segments.

    Only available when ``ENVIRONMENT=development`` and ``AUDIO_PIPELINE_ENGINE=mock``.
    Meetings processed this way are flagged ``is_demo`` so the UI labels them.
    """

    is_demo = True

    async def submit(
        self,
        audio_path: str,
        language: str = "vi",
        min_speakers: int = 1,
        max_speakers: int = 6,
    ) -> str:
        """Accept any file and return a job id that is immediately complete.

        Args:
            audio_path: Ignored.
            language: Ignored.
            min_speakers: Ignored.
            max_speakers: Ignored.

        Returns:
            A mock job id.
        """
        return f"mock-{uuid.uuid4().hex[:12]}"

    async def get_result(self, provider_job_id: str) -> TranscriptionResult:
        """Return the fixed demo transcript for any mock job.

        Args:
            provider_job_id: Ignored.

        Returns:
            A finished result with a copy of the demo segments.
        """
        return TranscriptionResult("done", [dict(segment) for segment in DEMO_SEGMENTS])
