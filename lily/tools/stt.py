"""Speech-to-text tools."""

from ..stt import STTUnavailable, transcribe_file
from . import tool


@tool(
    description="Transcribe a local audio file to text using faster-whisper. path must be a local audio file path."
)
def transcribe_audio(path: str, language: str = "") -> str:
    try:
        return transcribe_file(path, language=language)
    except STTUnavailable as exc:
        return f"[error] {exc}"
