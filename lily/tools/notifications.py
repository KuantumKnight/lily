"""Notification tools — let Lily queue and review her batched notifications."""

from .. import notifications
from . import tool


@tool(description="Queue a notification. priority: low, normal, high, or emergency. "
                  "high/emergency surface now; normal/low wait until Lily is active.")
def notify(content: str, priority: str = "normal", source: str = "") -> str:
    note = notifications.enqueue(content, priority, source)
    if note.priority in {"HIGH", "EMERGENCY"}:
        return f"Surfaced now [{note.priority}]: {note.content}"
    return f"Queued [{note.priority}] — will surface when Lily is active."


@tool(description="List the notifications Lily has batched and not yet surfaced.")
def list_notifications() -> str:
    items = notifications.pending()
    if not items:
        return "No pending notifications."
    return "\n".join(f"[{n.priority}] {n.content}" + (f" ({n.source})" if n.source else "") for n in items)
