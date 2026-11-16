from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AudioProcessorProtocol(Protocol):
    """Protocol defining the interface for an audio transcription and diarization processor."""

    async def process_audio(
        self,
        audio_path: str,
        language: str = "vi",
        min_speakers: int = 1,
        max_speakers: int = 6,
    ) -> list[dict[str, Any]]:
        """Process an audio file and return normalized transcript segments.

        Args:
            audio_path: Local filesystem path or remote HTTP/HTTPS URL.
            language: Spoken language code (e.g. 'vi').
            min_speakers: Lower bound estimate of speaker count.
            max_speakers: Upper bound estimate of speaker count.

        Returns:
            List of segment dictionaries with speaker label, timestamps, text, and words.
        """
        ...
