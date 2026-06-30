"""OCR tools — read screen text only when explicitly asked."""

from .. import ocr
from . import tool


@tool(
    description=(
        "Read visible text from a screenshot or from an explicit on-demand screen "
        "capture. Leave image_path empty to capture the screen first."
    )
)
def read_screen_text(image_path: str = "", monitor: int = 1) -> str:
    try:
        text = ocr.read_text(image_path=image_path, monitor=monitor)
    except ocr.OCRUnavailable as exc:
        return f"[error] {exc}"
    return text or "No readable text found."
