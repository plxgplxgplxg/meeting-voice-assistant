from typing import Any

import numpy as np
import structlog

logger = structlog.get_logger(__name__)


class VoiceActivityDetector:
    """Voice Activity Detector (VAD) processing 16 kHz Mono PCM audio buffers.

    Applies frame-level energy evaluation with adaptive thresholding and state tracking
    for speech/silence boundaries.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 32,
        energy_threshold: float = 0.015,
        min_speech_duration_ms: int = 200,
        min_silence_duration_ms: int = 400,
    ) -> None:
        """Initialize VoiceActivityDetector.

        Args:
            sample_rate: Audio sampling frequency in Hz (default 16000).
            frame_duration_ms: Frame window duration in milliseconds (default 32ms).
            energy_threshold: RMS amplitude threshold classifying speech presence.
            min_speech_duration_ms: Minimum consecutive speech length to validate a segment.
            min_silence_duration_ms: Silence gap required to close an ongoing speech segment.
        """
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * (frame_duration_ms / 1000.0))
        self.energy_threshold = energy_threshold
        self.min_speech_duration_ms = min_speech_duration_ms
        self.min_silence_duration_ms = min_silence_duration_ms

    def compute_frame_energy(self, frame: np.ndarray) -> float:
        """Compute Root Mean Square (RMS) energy of a single audio frame.

        Args:
            frame: 1D numpy array of float audio samples in [-1.0, 1.0].

        Returns:
            RMS energy value.
        """
        if len(frame) == 0:
            return 0.0
        return float(np.sqrt(np.mean(frame**2)))

    def detect_speech_segments(self, audio_data: bytes) -> list[dict[str, Any]]:
        """Extract validated speech segments with start and end times from raw PCM bytes.

        Args:
            audio_data: Raw 16-bit signed PCM mono audio bytes at sample_rate.

        Returns:
            List of dictionaries containing 'start', 'end', and 'is_speech' fields.
        """
        if len(audio_data) < self.frame_size * 2:
            return []

        # Convert raw int16 bytes to normalized float32 array in [-1.0, 1.0]
        audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        total_samples = len(audio_np)
        num_frames = total_samples // self.frame_size

        segments: list[dict[str, Any]] = []
        in_speech = False
        speech_start_sample = 0
        silence_start_sample = 0

        min_speech_samples = int(self.sample_rate * (self.min_speech_duration_ms / 1000.0))
        min_silence_samples = int(self.sample_rate * (self.min_silence_duration_ms / 1000.0))

        for i in range(num_frames):
            start_idx = i * self.frame_size
            end_idx = start_idx + self.frame_size
            frame = audio_np[start_idx:end_idx]

            energy = self.compute_frame_energy(frame)
            is_frame_speech = energy >= self.energy_threshold

            if not in_speech and is_frame_speech:
                in_speech = True
                speech_start_sample = start_idx
            elif in_speech:
                if not is_frame_speech:
                    if silence_start_sample == 0:
                        silence_start_sample = start_idx
                    elif (start_idx - silence_start_sample) >= min_silence_samples:
                        # Segment ended due to sufficient silence
                        segment_length = silence_start_sample - speech_start_sample
                        if segment_length >= min_speech_samples:
                            segments.append({
                                "start": round(speech_start_sample / self.sample_rate, 3),
                                "end": round(silence_start_sample / self.sample_rate, 3),
                                "is_speech": True,
                            })
                        in_speech = False
                        silence_start_sample = 0
                else:
                    silence_start_sample = 0

        # Close tail segment if active
        if in_speech:
            end_sample = silence_start_sample if silence_start_sample > 0 else total_samples
            if (end_sample - speech_start_sample) >= min_speech_samples:
                segments.append({
                    "start": round(speech_start_sample / self.sample_rate, 3),
                    "end": round(end_sample / self.sample_rate, 3),
                    "is_speech": True,
                })

        return segments
