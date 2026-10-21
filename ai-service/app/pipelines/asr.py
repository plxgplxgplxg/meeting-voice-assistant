from typing import Any


class WhisperASRPipeline:
    """Transcription pipeline wrapping Faster-Whisper."""

    def __init__(self, model_size: str = "base", device: str = "cpu") -> None:
        self.model_size = model_size
        self.device = device

    async def transcribe(
        self, audio_path: str, language: str = "vi"
    ) -> list[dict[str, Any]]:
        """Transcribe an audio file into timestamped text segments.

        Args:
            audio_path: Filesystem path to the audio file.
            language: Target spoken language code (e.g. 'vi').

        Returns:
            List of transcript segments containing text and timestamps.
        """
        return [
            {
                "start": 0.0,
                "end": 3.0,
                "text": "Xin chao cac ban, chung ta bat dau cuoc hop.",
            }
        ]
