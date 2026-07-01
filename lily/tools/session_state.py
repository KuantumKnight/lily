"""Sleep/wake state tools."""

from .. import session_state
from . import tool


@tool(description="Save Lily's current session state for wake after restart.")
def save_session_state(reason: str = "manual") -> str:
    return f"Saved session state to {session_state.save(reason)}"


@tool(description="Show the saved session-state wake summary.")
def wake_state() -> str:
    return session_state.restore_summary() or "No saved session state."
