import numpy as np
from app.pipelines.vad import VoiceActivityDetector


def test_vad_silence_detection() -> None:
    """Verify silence audio bytes produce no speech segments."""
    vad = VoiceActivityDetector(sample_rate=16000)
    # 1 second of pure silence (int16 zeros)
    silence_pcm = np.zeros(16000, dtype=np.int16).tobytes()
    segments = vad.detect_speech_segments(silence_pcm)
    assert len(segments) == 0


def test_vad_speech_tone_detection() -> None:
    """Verify audio containing tone signal generates speech segments."""
    vad = VoiceActivityDetector(sample_rate=16000, energy_threshold=0.01)
    # Generate 1 second of speech-like sine wave (440Hz, amplitude 0.5)
    t = np.linspace(0, 1.0, 16000, endpoint=False)
    sine_wave = (np.sin(2 * np.pi * 440 * t) * 16384).astype(np.int16)
    tone_pcm = sine_wave.tobytes()

    segments = vad.detect_speech_segments(tone_pcm)
    assert len(segments) >= 1
    assert segments[0]["is_speech"] is True
    assert segments[0]["start"] >= 0.0
