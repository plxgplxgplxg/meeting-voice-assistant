import os
from typing import Any

import httpx
import structlog

from app.core.config import ai_settings
from app.core.errors import ProviderError, ProviderNotConfiguredError
from app.pipelines.protocols import AudioProcessorProtocol, TranscriptionResult

logger = structlog.get_logger(__name__)


class GladiaAudioPipeline(AudioProcessorProtocol):
    """Audio processing through Gladia API v2 (Solaria-1).

    Handles batch speech-to-text, speaker diarization, and word-level timestamps.
    ``submit`` uploads and starts a job; ``get_result`` is a single status check.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 120.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize Gladia audio pipeline.

        Args:
            api_key: Gladia API token. Defaults to settings.gladia_api_key.
            base_url: Gladia API base URL. Defaults to settings.gladia_base_url.
            timeout: HTTP request timeout in seconds (uploads can be large).
            client: Shared HTTP client; a short-lived one is used when omitted.
        """
        self.api_key = api_key or ai_settings.gladia_api_key
        self.base_url = (base_url or ai_settings.gladia_base_url).rstrip("/")
        self.timeout = timeout
        self._client = client

    @property
    def headers(self) -> dict[str, str]:
        """Headers required for authenticating with Gladia API."""
        return {"x-gladia-key": self.api_key}

    async def submit(
        self,
        audio_path: str,
        language: str = "vi",
        min_speakers: int = 1,
        max_speakers: int = 6,
    ) -> str:
        """Upload the recording and create a transcription job.

        Args:
            audio_path: Local filesystem path of the recording.
            language: Spoken language code.
            min_speakers: Min speaker count hint.
            max_speakers: Max speaker count hint.

        Returns:
            The Gladia job id.

        Raises:
            ProviderNotConfiguredError: If no Gladia API key is configured.
            FileNotFoundError: If the audio file does not exist.
            ProviderError: If the upload or job creation fails.
        """
        if not self.api_key:
            raise ProviderNotConfiguredError("ASR provider not configured")
        try:
            audio_url = await self.upload_audio(audio_path)
            return await self.create_transcription_job(
                audio_url, language, min_speakers, max_speakers
            )
        except (RuntimeError, httpx.HTTPError) as exc:
            logger.error("gladia_submit_failed", error=str(exc))
            raise ProviderError(f"ASR provider failed: {exc}") from exc

    async def get_result(self, provider_job_id: str) -> TranscriptionResult:
        """Check the job state once.

        Args:
            provider_job_id: Gladia job id.

        Returns:
            Current state, with normalized segments when Gladia finished.

        Raises:
            ProviderNotConfiguredError: If no Gladia API key is configured.
            ProviderError: If Gladia cannot be reached or answers with an error status.
        """
        if not self.api_key:
            raise ProviderNotConfiguredError("ASR provider not configured")
        url = f"{self.base_url}/v2/pre-recorded/{provider_job_id}"
        try:
            response = await self._request("GET", url, headers=self.headers)
        except httpx.HTTPError as exc:
            raise ProviderError(f"ASR provider unreachable: {exc}") from exc
        if response.status_code != 200:
            raise ProviderError(f"ASR provider returned status {response.status_code}")

        data = response.json()
        status = data.get("status")
        if status == "done":
            return TranscriptionResult("done", self.parse_utterances_to_segments(data))
        if status == "error":
            return TranscriptionResult("error", error=str(data.get("error") or "Unknown error"))
        return TranscriptionResult("processing")

    async def upload_audio(self, audio_path: str) -> str:
        """Upload a local audio file to Gladia temporary storage.

        Remote URLs are deliberately not accepted: only files resolved inside the
        storage root are processed.

        Args:
            audio_path: Local filesystem path of the recording.

        Returns:
            Hosted audio_url string for pre-recorded transcription.

        Raises:
            FileNotFoundError: If the local audio file does not exist.
            RuntimeError: If the upload request fails.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found at: {audio_path}")

        with open(audio_path, "rb") as handle:
            response = await self._request(
                "POST",
                f"{self.base_url}/v2/upload",
                headers=self.headers,
                files={"audio": (os.path.basename(audio_path), handle)},
            )

        if response.status_code not in (200, 201):
            logger.error("gladia_upload_failed", status_code=response.status_code)
            raise RuntimeError(f"Gladia upload failed with status {response.status_code}")
        audio_url = response.json().get("audio_url")
        if not audio_url:
            raise RuntimeError("Gladia upload response did not include 'audio_url'")
        return str(audio_url)

    async def create_transcription_job(
        self,
        audio_url: str,
        language: str = "vi",
        min_speakers: int = 1,
        max_speakers: int = 6,
    ) -> str:
        """Start a transcription job with diarization enabled.

        Args:
            audio_url: Hosted URL of the audio file.
            language: Target spoken language code.
            min_speakers: Lower bound estimate of speaker count.
            max_speakers: Upper bound estimate of speaker count.

        Returns:
            The Gladia job id.

        Raises:
            RuntimeError: If job creation fails.
        """
        payload = {
            "audio_url": audio_url,
            "diarization": True,
            "model": "solaria-1",
            "language_config": {"languages": [language], "code_switching": True},
            "diarization_config": {"min_speakers": min_speakers, "max_speakers": max_speakers},
        }
        response = await self._request(
            "POST",
            f"{self.base_url}/v2/pre-recorded",
            headers={**self.headers, "Content-Type": "application/json"},
            json=payload,
        )
        if response.status_code not in (200, 201):
            logger.error("gladia_job_creation_failed", status_code=response.status_code)
            raise RuntimeError(f"Gladia job creation failed with status {response.status_code}")
        job_id = response.json().get("id")
        if not job_id:
            raise RuntimeError("Gladia job response missing 'id'")
        return str(job_id)

    def parse_utterances_to_segments(self, result_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Normalize Gladia transcription output into the unified transcript segment schema.

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
            speaker_label = (
                f"SPEAKER_{speaker_idx:02d}" if isinstance(speaker_idx, int) else str(speaker_idx)
            )
            words: list[dict[str, Any]] = [
                {
                    "w": w.get("word", "").strip(),
                    "s": int(round(float(w.get("start", 0.0)) * 1000)),
                    "e": int(round(float(w.get("end", 0.0)) * 1000)),
                    "p": float(w.get("confidence", 1.0)),
                }
                for w in u.get("words", [])
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

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        if self._client is not None:
            return await self._client.request(method, url, timeout=self.timeout, **kwargs)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            return await client.request(method, url, **kwargs)
