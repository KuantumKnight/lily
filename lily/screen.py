"""Opt-in screen capture for Lily's Prime vision layer.

Nothing here runs in the background. Callers must explicitly request a capture.
"""

from datetime import datetime
from pathlib import Path

from .config import SCREENSHOT_DIR


class ScreenCaptureUnavailable(RuntimeError):
    """Raised when screen capture dependencies or OS permissions are missing."""


def capture_screen(monitor: int = 1, output_path: str | None = None) -> Path:
    """Capture one monitor to a PNG and return the written path.

    Monitor ``1`` is the primary display in mss. ``0`` captures the virtual
    monitor spanning all displays.
    """
    try:
        import mss
        import mss.tools
    except ImportError as exc:
        raise ScreenCaptureUnavailable(
            "mss is not installed. Run: pip install -r requirements.txt"
        ) from exc

    if monitor < 0:
        raise ScreenCaptureUnavailable("monitor must be 0 or greater")

    out = Path(output_path).expanduser() if output_path else _default_path()
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        with mss.mss() as sct:
            if monitor >= len(sct.monitors):
                available = len(sct.monitors) - 1
                raise ScreenCaptureUnavailable(
                    f"monitor {monitor} is unavailable; choose 0 through {available}"
                )
            shot = sct.grab(sct.monitors[monitor])
            mss.tools.to_png(shot.rgb, shot.size, output=str(out))
    except ScreenCaptureUnavailable:
        raise
    except Exception as exc:
        raise ScreenCaptureUnavailable(f"screen capture failed: {exc}") from exc

    return out


def _default_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return SCREENSHOT_DIR / f"screen-{stamp}.png"
