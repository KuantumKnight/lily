"""Sleep/wake state preservation across restarts."""

import json
import time
from pathlib import Path

from . import focus, memory, mode, notifications
from .config import SESSION_STATE_PATH


def snapshot(reason: str = "manual") -> dict:
    """Build a serializable snapshot of Lily's current local state."""
    return {
        "ts": time.time(),
        "reason": reason,
        "mode": mode.current(),
        "active_project": memory.active_project(),
        "focus": focus.status(),
        "pending_notifications": [
            {
                "content": note.content,
                "priority": note.priority,
                "source": note.source,
                "ts": note.ts,
            }
            for note in notifications.pending()
        ],
        "recent_messages": memory.recent(6),
    }


def save(reason: str = "sleep") -> Path:
    """Persist Lily's state for the next wake."""
    SESSION_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SESSION_STATE_PATH.write_text(
        json.dumps(snapshot(reason), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return SESSION_STATE_PATH


def load() -> dict:
    if not SESSION_STATE_PATH.exists():
        return {}
    try:
        return json.loads(SESSION_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def restore_summary() -> str:
    state = load()
    if not state:
        return ""
    parts = []
    if state.get("active_project"):
        parts.append(f"project={state['active_project']}")
    if state.get("mode"):
        parts.append(f"mode={state['mode']}")
    pending = state.get("pending_notifications") or []
    if pending:
        parts.append(f"{len(pending)} pending notification(s)")
    return "Restored previous state: " + ", ".join(parts) if parts else ""
