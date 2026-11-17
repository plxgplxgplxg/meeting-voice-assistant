import asyncio
import os
from typing import Any

import httpx
import structlog

from app.core.config import ai_settings
from app.core.errors import ProviderError, ProviderNotConfiguredError
from app.pipelines.protocols import AudioProcessorProtocol

logger = structlog.get_logger(__name__)


class GladiaAudioPipeline(AudioProcessorProtocol):
    """Audio processing pipeline utilizing Gladia API v2 (Solaria-1).

    Handles batch speech-to-text, speaker diarization, and word-level timestamps.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        """Initialize Gladia audio pipeline.

        Args:
            api_key: Gladia API token. Defaults to settings.gladia_api_key.
            base_url: Gladia API base URL. Defaults to settings.gladia_base_url.
            timeout: HTTP request timeout in seconds.
        """
        self.api_key = api_key or ai_settings.gladia_api_key
        self.base_url = (base_url or ai_settings.gladia_base_url).rstrip("/")
        self.timeout = timeout

    @property
    def headers(self) -> dict[str, str]:
        """Headers required for authenticating with Gladia API."""
        return {
            "x-gladia-key": self.api_key,
        }

    async def upload_audio(self, audio_path: str) -> str:
        """Upload a local audio file to Gladia temporary storage.

        Remote URLs are deliberately not accepted: the service only processes
        files that were resolved inside the storage root.

        Args:
            audio_path: Local filesystem path of the recording.

        Returns:
            Hosted audio_url string for pre-recorded transcription.

        Raises:
            FileNotFoundError: If the local audio file does not exist.
            RuntimeError: If upload request fails.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found at: {audio_path}")

        upload_url = f"{self.base_url}/v2/upload"
        filename = os.path.basename(audio_path)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            with open(audio_path, "rb") as f:
                files = {"audio": (filename, f)}
                response = await client.post(upload_url, headers=self.headers, files=files)

        if response.status_code not in (200, 201):
            logger.error("gladia_upload_failed", status_code=response.status_code, body=response.text)
            raise RuntimeError(f"Gladia upload failed with status {response.status_code}: {response.text}")

        data = response.json()
        audio_url = data.get("audio_url")
        if not audio_url:
            raise RuntimeError("Gladia upload response did not include 'audio_url'")

        logger.info("gladia_upload_success", audio_url=audio_url)
        return str(audio_url)

    async def create_transcription_job(
        self,
        audio_url: str,
        language: str = "vi",
        min_speakers: int = 1,
        max_speakers: int = 6,
    ) -> tuple[str, str]:
        """Initiate an asynchronous transcription job with diarization enabled.

        Args:
            audio_url: Hosted URL of the audio file to transcribe.
            language: Target spoken language code (default 'vi').
            min_speakers: Lower bound estimate of speaker count.
            max_speakers: Upper bound estimate of speaker count.

        Returns:
            Tuple of (job_id, result_url).

        Raises:
            RuntimeError: If job creation fails.
        """
        transcribe_url = f"{self.base_url}/v2/pre-recorded"
        payload = {
            "audio_url": audio_url,
            "diarization": True,
            "model": "solaria-1",
            "language_config": {
                "languages": [language],
                "code_switching": True,
            },
            "diarization_config": {
                "min_speakers": min_speakers,
                "max_speakers": max_speakers,
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                transcribe_url,
                headers={**self.headers, "Content-Type": "application/json"},
                json=payload,
            )

        if response.status_code not in (200, 201):
            logger.error("gladia_job_creation_failed", status_code=response.status_code, body=response.text)
            raise RuntimeError(f"Gladia job creation failed: {response.text}")

        data = response.json()
        job_id = data.get("id")
        result_url = data.get("result_url")
        if not job_id or not result_url:
            raise RuntimeError("Gladia job response missing 'id' or 'result_url'")

        logger.info("gladia_job_created", job_id=job_id, result_url=result_url)
        return str(job_id), str(result_url)

    async def poll_transcription_result(
        self,
        result_url: str,
        max_wait_seconds: int = 300,
        poll_interval: float = 3.0,
    ) -> dict[str, Any]:
        """Poll the Gladia job status until processing completes.

        Args:
            result_url: Polling URL returned by create_transcription_job.
            max_wait_seconds: Maximum time to wait before timing out.
            poll_interval: Interval between polling attempts in seconds.

        Returns:
            Complete Gladia response payload dictionary.

        Raises:
            TimeoutError: If processing exceeds max_wait_seconds.
            RuntimeError: If the transcription job reports an error.
        """
        elapsed = 0.0
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while elapsed < max_wait_seconds:
                response = await client.get(result_url, headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    logger.debug("gladia_polling_status", status=status, elapsed=elapsed)

                    if status == "done":
                        logger.info("gladia_transcription_completed", elapsed=elapsed)
                        return data
                    if status == "error":
                        error_detail = data.get("error", "Unknown error")
                        raise RuntimeError(f"Gladia transcription job failed: {error_detail}")

                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

        raise TimeoutError(f"Gladia transcription timed out after {max_wait_seconds} seconds")

    def parse_utterances_to_segments(self, result_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Normalize Gladia transcription output into unified transcript segment schema.

        Args:
            result_data: JSON payload from Gladia transcription result.

        Returns:
            List of standardized segment dictionaries with speaker labels and words.
        """
        transcription = result_data.get("result", {}).get("transcription", {})
        utterances = transcription.get("utterances", [])

        segments: list[dict[str, Any]] = []
        for idx, u in enumerate(utterances):
            speaker_idx = u.get("speaker", 0)
            speaker_label = f"SPEAKER_{speaker_idx:02d}" if isinstance(speaker_idx, int) else str(speaker_idx)

            raw_words = u.get("words", [])
            words: list[dict[str, Any]] = [
                {
                    "w": w.get("word", "").strip(),
                    "s": int(round(float(w.get("start", 0.0)) * 1000)),
                    "e": int(round(float(w.get("end", 0.0)) * 1000)),
                    "p": float(w.get("confidence", 1.0)),
                }
                for w in raw_words
                if w.get("word", "").strip()
            ]

            start_sec = float(u.get("start", 0.0))
            end_sec = float(u.get("end", 0.0))

            segments.append(
                {
                    "segment_id": u.get("id", idx),
                    "speaker": speaker_label,
                    "start": start_sec,
                    "end": end_sec,
                    "start_ms": int(round(start_sec * 1000)),
                    "end_ms": int(round(end_sec * 1000)),
                    "text": u.get("text", "").strip(),
                    "confidence": float(u.get("confidence", 1.0)),
                    "words": words,
                }
            )

        return segments

    async def process_audio(
        self,
        audio_path: str,
        language: str = "vi",
        min_speakers: int = 1,
        max_speakers: int = 6,
    ) -> list[dict[str, Any]]:
        """Orchestrate end-to-end transcription: upload -> submit job -> poll -> format.

        Args:
            audio_path: Filesystem path to the audio file.
            language: Spoken language code.
            min_speakers: Min speaker count hint.
            max_speakers: Max speaker count hint.

        Returns:
            List of standardized transcript segment dictionaries.

        Raises:
            ProviderNotConfiguredError: If no Gladia API key is configured.
            FileNotFoundError: If the audio file does not exist.
            ProviderError: If Gladia fails, errors, or times out.
        """
        if not self.api_key:
            raise ProviderNotConfiguredError("ASR provider not configured")

        try:
            audio_url = await self.upload_audio(audio_path)
            _, result_url = await self.create_transcription_job(
                audio_url=audio_url,
                language=language,
                min_speakers=min_speakers,
                max_speakers=max_speakers,
            )
            result_data = await self.poll_transcription_result(
                result_url, max_wait_seconds=ai_settings.gladia_max_wait_seconds
            )
        except (RuntimeError, TimeoutError, httpx.HTTPError) as exc:
            logger.error("gladia_pipeline_failed", error=str(exc))
            raise ProviderError(f"ASR provider failed: {exc}") from exc
        return self.parse_utterances_to_segments(result_data)
