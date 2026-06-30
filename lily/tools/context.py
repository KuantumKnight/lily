"""Context-fusion tools."""

from .. import context
from . import tool


@tool(
    description=(
        "Build an explicit on-demand snapshot of what the user is doing by combining "
        "active window, git status, screen OCR, and optional local vision."
    )
)
def current_context(include_vision: bool = True, monitor: int = 1) -> str:
    return context.snapshot(include_vision=include_vision, monitor=monitor)
