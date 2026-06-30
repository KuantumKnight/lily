"""Decision memory tools."""

from .. import decisions
from . import tool


@tool(description="Remember a decision together with why it was made.")
def remember_decision(decision: str, reason: str, context: str = "") -> str:
    try:
        decision_id = decisions.remember(decision, reason, context)
    except ValueError as exc:
        return f"[error] {exc}"
    return f"Remembered decision #{decision_id}."


@tool(description="Search remembered decisions and reasons.")
def search_decisions(query: str = "", limit: int = 20) -> str:
    return decisions.format_rows(decisions.search(query, limit))
