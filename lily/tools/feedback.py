"""Feedback tools."""

from .. import feedback
from . import tool


@tool(description="Record feedback with an optional reason/context and update preference signals.")
def record_feedback(rating: str, target: str, reason: str = "", context: str = "") -> str:
    try:
        feedback_id = feedback.record(rating, target, reason, context)
    except ValueError as exc:
        return f"[error] {exc}"
    return f"Recorded feedback #{feedback_id}."


@tool(description="Summarize Lily's learned preference signals from feedback.")
def feedback_preferences(limit: int = 12) -> str:
    return feedback.summary(limit)
