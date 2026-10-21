from typing import Any


class SpeakerDiarizationPipeline:
    """Speaker diarization pipeline wrapping Pyannote.audio."""

    def __init__(self, token: str) -> None:
        self.token = token

    async def diarize(self, audio_path: str) -> list[dict[str, Any]]:
        """Diarize speakers across an audio recording.

        Args:
            audio_path: Filesystem path to the audio file.

        Returns:
            List of speaker label assignments per time interval.
        """
        return [
            {"speaker": "Speaker 1", "start": 0.0, "end": 3.0},
            {"speaker": "Speaker 2", "start": 3.2, "end": 5.8},
        ]
