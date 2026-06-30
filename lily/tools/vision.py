"""Vision tools — local Ollama image understanding on explicit request."""

from .. import vision
from . import tool


@tool(
    description=(
        "Use the configured local Ollama vision model to understand a screenshot "
        "or image. Leave image_path empty to capture the screen first."
    )
)
def inspect_screen(prompt: str = "", image_path: str = "", monitor: int = 1) -> str:
    try:
        return vision.describe_image(prompt=prompt, image_path=image_path, monitor=monitor)
    except vision.VisionUnavailable as exc:
        return f"[error] {exc}"
