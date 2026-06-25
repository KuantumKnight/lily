"""Text-to-speech tools."""

from ..tts import TTSUnavailable, speak
from . import tool


@tool(
    description="Speak text aloud with Lily's Piper voice. Use when the user asks you to say something out loud."
)
def speak_text(text: str) -> str:
    try:
        speak(text)
        return "[spoke aloud]"
    except TTSUnavailable as exc:
        return f"[error] {exc}"
