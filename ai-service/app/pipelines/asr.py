from typing import Any
import structlog

from app.core.config import ai_settings
from app.pipelines.gladia import GladiaAudioPipeline
from app.pipelines.protocols import AudioProcessorProtocol

logger = structlog.get_logger(__name__)


class WhisperASRPipeline:
    """ASR transcription pipeline.

    In API-first mode, delegates to an AudioProcessorProtocol implementation (default GladiaAudioPipeline).
    """

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        processor: AudioProcessorProtocol | None = None,
    ) -> None:
        """Initialize WhisperASRPipeline with an injected audio processor.

        Args:
            model_size: Whisper model size tag.
            device: Computing device ('cpu' or 'cuda').
            processor: Concrete audio processor instance implementing AudioProcessorProtocol.
        """
        self.model_size = model_size
        self.device = device
        self.processor = processor or GladiaAudioPipeline()
        self.gladia_pipeline = self.processor

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
        logger.info("transcribing_audio", path=audio_path, language=language)
        return await self.processor.process_audio(audio_path, language=language)
