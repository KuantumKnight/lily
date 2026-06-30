"""On-demand OCR for Lily's screen-reading layer."""

from pathlib import Path

from . import screen


class OCRUnavailable(RuntimeError):
    """Raised when OCR dependencies, input files, or capture permissions fail."""


def read_text(
    image_path: str = "",
    monitor: int = 1,
    min_confidence: float = 0.3,
) -> str:
    """Read text from an image, or capture a screen first when no path is given."""
    path = Path(image_path).expanduser() if image_path else screen.capture_screen(monitor)
    if not path.exists():
        raise OCRUnavailable(f"image not found: {path}")

    try:
        engine = _engine()
        raw = engine(str(path))
    except screen.ScreenCaptureUnavailable as exc:
        raise OCRUnavailable(str(exc)) from exc
    except ImportError as exc:
        raise OCRUnavailable(
            "RapidOCR is not installed. Run: pip install -r requirements.txt"
        ) from exc
    except Exception as exc:
        raise OCRUnavailable(f"OCR failed: {exc}") from exc

    lines = _extract_lines(raw, min_confidence)
    return "\n".join(lines).strip()


def _engine():
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        from rapidocr import RapidOCR
    return RapidOCR()


def _extract_lines(raw, min_confidence: float) -> list[str]:
    results = raw[0] if isinstance(raw, tuple) else raw
    if not results:
        return []

    lines: list[str] = []
    for item in results:
        text, score = _item_text_score(item)
        if text and score >= min_confidence:
            lines.append(text)
    return lines


def _item_text_score(item) -> tuple[str, float]:
    if isinstance(item, dict):
        text = item.get("text") or item.get("rec_txt") or ""
        score = item.get("score") or item.get("rec_score") or 1.0
        return str(text).strip(), float(score)
    if isinstance(item, (list, tuple)) and len(item) >= 3:
        return str(item[1]).strip(), float(item[2])
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        return str(item[0]).strip(), float(item[1])
    return str(item).strip(), 1.0
