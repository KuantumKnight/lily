"""Anti-distraction focus tools."""

from .. import focus
from . import tool


@tool(description="Start a focus block; normal/low notifications stay batched.")
def start_focus(minutes: int = 25, reason: str = "focus") -> str:
    return focus.start(minutes=minutes, reason=reason)


@tool(description="End the current focus block.")
def end_focus() -> str:
    return focus.end()


@tool(description="Show current focus protection status.")
def focus_status() -> str:
    return focus.status()
