"""Text-to-speech through Piper — Lily's spoken voice."""

import tempfile
import wave
from pathlib import Path

from .config import TTS_VOICE
from .log import get_logger

log = get_logger("tts")
_VOICE = None
_ASYNC_TMP = None  # path of the temp WAV currently playing via speak_async


class TTSUnavailable(Exception):
    """Raised when text-to-speech dependencies or the voice model are unavailable."""


def _load_voice():
    global _VOICE
    if _VOICE is not None:
        return _VOICE

    try:
        from piper import PiperVoice
    except ImportError as exc:
        raise TTSUnavailable(
            "piper-tts is not installed. Run: pip install -r requirements.txt"
        ) from exc

    if not TTS_VOICE:
        raise TTSUnavailable(
            "No Piper voice configured. Set tts_voice to a .onnx voice path "
            "(download from https://huggingface.co/rhasspy/piper-voices)."
        )
    voice_path = Path(TTS_VOICE).expanduser()
    if not voice_path.exists():
        raise TTSUnavailable(f"Piper voice not found: {voice_path}")

    log.info("loading piper voice=%s", voice_path)
    _VOICE = PiperVoice.load(str(voice_path))
    return _VOICE


def synthesize_to_file(text: str, path: str) -> str:
    """Synthesize ``text`` to a WAV file and return its path."""
    clean = text.strip()
    if not clean:
        raise TTSUnavailable("nothing to speak")

    voice = _load_voice()
    out_path = Path(path).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as wav_file:
        voice.synthesize_wav(clean, wav_file)
    return str(out_path)


def speak(text: str) -> None:
    """Synthesize ``text`` and play it aloud (blocking)."""
    import winsound

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        synthesize_to_file(text, tmp_path)
        winsound.PlaySound(tmp_path, winsound.SND_FILENAME)
    finally:
        try:
            Path(tmp_path).unlink()
        except OSError:
            pass


def _wav_seconds(path: str) -> float:
    with wave.open(path, "rb") as wav_file:
        rate = wav_file.getframerate() or 1
        return wav_file.getnframes() / float(rate)


def speak_async(text: str) -> float:
    """Start playing ``text`` without blocking. Returns the clip length in seconds.

    Pair with :func:`stop` for barge-in — call ``stop()`` to cut playback short.
    """
    import winsound

    clean = text.strip()
    if not clean:
        return 0.0
    stop()  # cancel anything already playing and drop its temp file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    synthesize_to_file(clean, tmp_path)
    winsound.PlaySound(tmp_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    global _ASYNC_TMP
    _ASYNC_TMP = tmp_path
    return _wav_seconds(tmp_path)


def stop() -> None:
    """Stop any in-progress async playback and clean up its temp file."""
    global _ASYNC_TMP
    try:
        import winsound

        winsound.PlaySound(None, winsound.SND_PURGE)
    except Exception:  # no audio device / not Windows — nothing to stop
        pass
    if _ASYNC_TMP:
        try:
            Path(_ASYNC_TMP).unlink()
        except OSError:
            pass
        _ASYNC_TMP = None
