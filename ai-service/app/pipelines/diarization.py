from typing import Any
import structlog

from app.pipelines.gladia import GladiaAudioPipeline
from app.pipelines.protocols import AudioProcessorProtocol

logger = structlog.get_logger(__name__)


class SpeakerDiarizationPipeline:
    """Speaker diarization pipeline.

    In API-first mode, speaker diarization is natively handled by an AudioProcessorProtocol implementation.
    """

    def __init__(
        self,
        token: str = "",
        processor: AudioProcessorProtocol | None = None,
    ) -> None:
        """Initialize SpeakerDiarizationPipeline.

        Args:
            token: Legacy HF/Pyannote auth token (preserved for backward compatibility).
            processor: Concrete audio processor instance implementing AudioProcessorProtocol.
        """
        self.token = token
        self.processor = processor or GladiaAudioPipeline()
        self.gladia_pipeline = self.processor

    async def diarize(self, audio_path: str) -> list[dict[str, Any]]:
        """Diarize speakers across an audio recording.

        Args:
            audio_path: Filesystem path to the audio file.

        Returns:
            List of speaker label assignments per time interval.
        """
        logger.info("diarizing_audio", path=audio_path)
        segments = await self.processor.process_audio(audio_path)
        return [
            {
                "speaker": seg["speaker"],
                "start": seg["start"],
                "end": seg["end"],
            }
            for seg in segments
        ]
