from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

TranscriptionState = Literal["processing", "done", "error"]


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    """State of one asynchronous transcription job at the provider.

    Attributes:
        status: ``processing`` while the provider works, ``done`` with segments, or ``error``.
        segments: Normalized transcript segments once done.
        error: Provider error message when ``status`` is ``error``.
    """

    status: TranscriptionState
    segments: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


@runtime_checkable
class AudioProcessorProtocol(Protocol):
    """Interface of an asynchronous audio transcription and diarization provider.

    Transcription is split into submit and poll so no HTTP request has to stay open
    for the duration of a long recording.
    """

    async def submit(
        self,
        audio_path: str,
        language: str = "vi",
        min_speakers: int = 1,
        max_speakers: int = 6,
    ) -> str:
        """Start transcribing a file and return immediately with a provider job id.

        Args:
            audio_path: Local filesystem path inside the storage root.
            language: Spoken language code (e.g. 'vi').
            min_speakers: Lower bound estimate of speaker count.
            max_speakers: Upper bound estimate of speaker count.

        Returns:
            Provider job id to pass to :meth:`get_result`.
        """
        ...

    async def get_result(self, provider_job_id: str) -> TranscriptionResult:
        """Check a job once, without waiting.

        Args:
            provider_job_id: Id returned by :meth:`submit`.

        Returns:
            Current status, with segments when finished.
        """
        ...
