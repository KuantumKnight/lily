"""Microphone capture with silence-based end-of-utterance detection."""

from .config import MIC_MAX_SECONDS, MIC_SILENCE_SECONDS, MIC_SILENCE_THRESHOLD
from .log import get_logger

log = get_logger("mic")

SAMPLE_RATE = 16000  # whisper's native rate — no resampling needed
FRAME_MS = 100
FRAME_SIZE = SAMPLE_RATE * FRAME_MS // 1000


class MicUnavailable(Exception):
    """Raised when no microphone is available or audio capture fails."""


def record_until_silence(start_timeout: float = 8.0):
    """Record one spoken utterance and return float32 samples at 16kHz.

    Waits up to ``start_timeout`` for speech to begin; once the speaker pauses for
    ``MIC_SILENCE_SECONDS`` (or ``MIC_MAX_SECONDS`` elapses) recording stops.
    Returns an empty array if no speech was heard.
    """
    try:
        import numpy as np
        import sounddevice as sd
    except ImportError as exc:
        raise MicUnavailable(
            "sounddevice/numpy not installed. Run: pip install -r requirements.txt"
        ) from exc

    try:
        stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=FRAME_SIZE
        )
    except Exception as exc:
        raise MicUnavailable(f"no usable microphone: {exc}") from exc

    dt = FRAME_MS / 1000
    frames: list = []
    speech_started = False
    silent = 0.0
    elapsed = 0.0
    waited = 0.0

    with stream:
        while True:
            data, _ = stream.read(FRAME_SIZE)
            frame = np.frombuffer(data, dtype=np.int16)
            rms = float(np.sqrt(np.mean(frame.astype(np.float32) ** 2)))

            if not speech_started:
                if rms >= MIC_SILENCE_THRESHOLD:
                    speech_started = True
                    frames.append(frame)
                else:
                    waited += dt
                    if waited >= start_timeout:
                        return np.zeros(0, dtype=np.float32)
                continue

            frames.append(frame)
            elapsed += dt
            if rms < MIC_SILENCE_THRESHOLD:
                silent += dt
                if silent >= MIC_SILENCE_SECONDS:
                    break
            else:
                silent = 0.0
            if elapsed >= MIC_MAX_SECONDS:
                break

    audio = np.concatenate(frames).astype(np.float32) / 32768.0
    return audio
