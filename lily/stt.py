"""Speech-to-text through faster-whisper."""

from pathlib import Path

from .config import STT_COMPUTE_TYPE, STT_DEVICE, STT_MODEL
from .log import get_logger

log = get_logger("stt")
_MODEL = None


class STTUnavailable(Exception):
    """Raised when speech-to-text dependencies or inputs are unavailable."""


def _load_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise STTUnavailable(
            "faster-whisper is not installed. Run: pip install -r requirements.txt"
        ) from exc

    log.info(
        "loading faster-whisper model=%s device=%s compute_type=%s",
        STT_MODEL,
        STT_DEVICE,
        STT_COMPUTE_TYPE,
    )
    _MODEL = WhisperModel(
        STT_MODEL,
        device=STT_DEVICE,
        compute_type=STT_COMPUTE_TYPE,
    )
    return _MODEL


def _run(audio, language: str):
    """Transcribe an audio source (path or float32 array). Returns (text, info)."""
    model = _load_model()
    kwargs = {"vad_filter": True}
    if language.strip():
        kwargs["language"] = language.strip()
    segments, info = model.transcribe(audio, **kwargs)
    text = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
    return text, info


def transcribe_file(path: str, language: str = "") -> str:
    """Transcribe one local audio file and return plain text with light metadata."""
    audio_path = Path(path).expanduser()
    if not audio_path.exists():
        raise STTUnavailable(f"audio file not found: {audio_path}")
    if not audio_path.is_file():
        raise STTUnavailable(f"audio path is not a file: {audio_path}")

    text, info = _run(str(audio_path), language)
    if not text:
        return "[no speech detected]"

    detected = getattr(info, "language", "unknown")
    probability = getattr(info, "language_probability", 0.0)
    return f"{text}\n\n[language: {detected}, probability: {probability:.2f}]"


def transcribe_array(samples, language: str = "") -> str:
    """Transcribe float32 mono samples at 16kHz and return plain text (no metadata)."""
    if samples is None or len(samples) == 0:
        return ""
    text, _ = _run(samples, language)
    return text
