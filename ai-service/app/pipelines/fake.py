from typing import Any

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

    async def process_audio(
        self,
        audio_path: str,
        language: str = "vi",
        min_speakers: int = 1,
        max_speakers: int = 6,
    ) -> list[dict[str, Any]]:
        """Return the fixed demo transcript regardless of the input.

        Args:
            audio_path: Ignored.
            language: Ignored.
            min_speakers: Ignored.
            max_speakers: Ignored.

        Returns:
            A copy of the demo segments.
        """
        return [dict(segment) for segment in DEMO_SEGMENTS]
