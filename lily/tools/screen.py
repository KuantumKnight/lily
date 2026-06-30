"""Screen tools — opt-in, on-demand capture only."""

from .. import screen
from . import tool


@tool(
    description=(
        "Capture the user's screen to a local PNG only when explicitly asked. "
        "Use monitor 1 for the primary display or 0 for all displays."
    )
)
def capture_screen(monitor: int = 1) -> str:
    try:
        path = screen.capture_screen(monitor=monitor)
    except screen.ScreenCaptureUnavailable as exc:
        return f"[error] {exc}"
    return f"Captured screen to {path}"
