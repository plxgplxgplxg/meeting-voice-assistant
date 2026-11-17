import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.core.errors import DomainError, ValidationFailedError

PROBE_TIMEOUT_SECONDS = 60.0


@dataclass(frozen=True, slots=True)
class AudioMetadata:
    """Facts about a recording discovered by probing the file.

    Attributes:
        duration_seconds: Real playback duration.
        codec: Audio codec name, when known.
        container: Container format name, when known.
    """

    duration_seconds: float
    codec: str | None = None
    container: str | None = None


class AudioProbe(Protocol):
    """Seam for inspecting an audio file before it is sent for transcription."""

    async def probe(self, path: Path) -> AudioMetadata:
        """Read duration and codec from a file.

        Args:
            path: Absolute path of the recording.

        Returns:
            Probed metadata.

        Raises:
            ValidationFailedError: If the file contains no decodable audio stream.
        """
        ...


class FfprobeAudioProbe:
    """Probe adapter that shells out to ``ffprobe``."""

    def __init__(self, executable: str = "ffprobe") -> None:
        """Initialize the adapter.

        Args:
            executable: ffprobe binary name or path.
        """
        self.executable = executable

    async def probe(self, path: Path) -> AudioMetadata:
        command = [
            self.executable,
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
        try:
            process = await asyncio.create_subprocess_exec(
                *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
        except FileNotFoundError as exc:
            raise DomainError(
                "ffprobe is not installed.", code="PROBE_UNAVAILABLE", status_code=500
            ) from exc

        try:
            stdout, _ = await asyncio.wait_for(process.communicate(), PROBE_TIMEOUT_SECONDS)
        except TimeoutError as exc:
            process.kill()
            raise ValidationFailedError(
                "Audio probing timed out.", code="INVALID_AUDIO_CONTENT"
            ) from exc

        if process.returncode != 0:
            raise ValidationFailedError(
                "The file is not a readable audio or video recording.",
                code="INVALID_AUDIO_CONTENT",
            )
        return self._parse(stdout)

    @staticmethod
    def _parse(raw: bytes) -> AudioMetadata:
        """Turn ffprobe JSON into metadata, rejecting files with no audio stream."""
        data = json.loads(raw or b"{}")
        audio_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
        if not audio_streams:
            raise ValidationFailedError(
                "The file contains no audio stream.", code="INVALID_AUDIO_CONTENT"
            )
        stream = audio_streams[0]
        raw_duration = data.get("format", {}).get("duration") or stream.get("duration")
        try:
            duration = float(raw_duration)
        except (TypeError, ValueError) as exc:
            raise ValidationFailedError(
                "The recording duration could not be determined.", code="INVALID_AUDIO_CONTENT"
            ) from exc
        if duration <= 0:
            raise ValidationFailedError("The recording is empty.", code="INVALID_AUDIO_CONTENT")
        return AudioMetadata(
            duration_seconds=duration,
            codec=stream.get("codec_name"),
            container=data.get("format", {}).get("format_name"),
        )
