"""Local vision model support via Ollama."""

from pathlib import Path

import ollama

from . import screen
from .config import OLLAMA_HOST, VISION_MODEL
from .log import get_logger

log = get_logger("vision")
_client = ollama.Client(host=OLLAMA_HOST)


class VisionUnavailable(RuntimeError):
    """Raised when the local vision model cannot be reached or used."""


def describe_image(
    prompt: str = "Describe what is visible. Focus on UI state, errors, and actionable details.",
    image_path: str = "",
    monitor: int = 1,
) -> str:
    """Ask the configured local vision model to understand an image."""
    path = Path(image_path).expanduser() if image_path else screen.capture_screen(monitor)
    if not path.exists():
        raise VisionUnavailable(f"image not found: {path}")

    try:
        response = _client.chat(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt.strip() or "Describe this image.",
                    "images": [str(path)],
                }
            ],
        )
    except screen.ScreenCaptureUnavailable as exc:
        raise VisionUnavailable(str(exc)) from exc
    except ollama.ResponseError as exc:
        if "not found" in str(exc).lower():
            raise VisionUnavailable(
                f"Vision model '{VISION_MODEL}' is not pulled. Run: ollama pull {VISION_MODEL}"
            ) from exc
        raise VisionUnavailable(str(exc)) from exc
    except Exception as exc:
        log.error("cannot reach ollama vision model at %s: %s", OLLAMA_HOST, exc)
        raise VisionUnavailable(
            f"Can't reach Ollama at {OLLAMA_HOST}. Is it running? (ollama serve)"
        ) from exc

    message = response.get("message", {}) if isinstance(response, dict) else response.message
    content = message.get("content", "") if isinstance(message, dict) else message.content
    return str(content).strip()
