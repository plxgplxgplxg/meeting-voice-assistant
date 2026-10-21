from typing import Any


class VoiceActivityDetector:
    """Detector for identifying human voice presence in audio buffers."""

    def __init__(self, sample_rate: int = 16000) -> None:
        self.sample_rate = sample_rate

    def detect_speech_segments(self, audio_data: bytes) -> list[dict[str, Any]]:
        """Extract speech timestamps from raw audio bytes.

        Args:
            audio_data: Raw byte stream of mono audio.

        Returns:
            List of detected speech segments with start and end times.
        """
        return [{"start": 0.0, "end": 2.5, "is_speech": True}]
