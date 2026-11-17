import json
import math
import shutil
import struct
import wave
from pathlib import Path

import pytest

from app.core.errors import ValidationFailedError
from app.services.audio_probe import FfprobeAudioProbe


def ffprobe_json(streams: list[dict], duration: str | None) -> bytes:
    data: dict = {"streams": streams, "format": {"format_name": "wav"}}
    if duration is not None:
        data["format"]["duration"] = duration
    return json.dumps(data).encode()


def test_parse_reads_duration_codec_and_container() -> None:
    raw = ffprobe_json([{"codec_type": "audio", "codec_name": "mp3"}], "12.5")
    metadata = FfprobeAudioProbe._parse(raw)
    assert (metadata.duration_seconds, metadata.codec, metadata.container) == (12.5, "mp3", "wav")


@pytest.mark.parametrize(
    "raw",
    [
        ffprobe_json([{"codec_type": "video"}], "10"),
        ffprobe_json([], "10"),
        ffprobe_json([{"codec_type": "audio"}], None),
        ffprobe_json([{"codec_type": "audio"}], "0"),
        ffprobe_json([{"codec_type": "audio"}], "not-a-number"),
    ],
)
def test_parse_rejects_files_without_usable_audio(raw: bytes) -> None:
    with pytest.raises(ValidationFailedError) as exc:
        FfprobeAudioProbe._parse(raw)
    assert exc.value.code == "INVALID_AUDIO_CONTENT"


def write_tone(path: Path, seconds: float = 1.5, rate: int = 8000) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        frames = b"".join(
            struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / rate)))
            for i in range(int(seconds * rate))
        )
        handle.writeframes(frames)


@pytest.mark.skipif(shutil.which("ffprobe") is None, reason="ffprobe is not installed")
@pytest.mark.asyncio
async def test_real_ffprobe_measures_duration_and_rejects_garbage(tmp_path: Path) -> None:
    probe = FfprobeAudioProbe()
    good = tmp_path / "tone.wav"
    write_tone(good)
    metadata = await probe.probe(good)
    assert metadata.duration_seconds == pytest.approx(1.5, abs=0.05)
    assert metadata.codec == "pcm_s16le"

    bad = tmp_path / "fake.wav"
    bad.write_bytes(b"RIFF" + b"\x00" * 64)
    with pytest.raises(ValidationFailedError):
        await probe.probe(bad)


@pytest.mark.asyncio
async def test_missing_ffprobe_binary_is_reported_as_a_server_problem(tmp_path: Path) -> None:
    from app.core.errors import DomainError

    with pytest.raises(DomainError) as exc:
        await FfprobeAudioProbe(executable="definitely-not-installed").probe(tmp_path / "x.wav")
    assert exc.value.code == "PROBE_UNAVAILABLE"
