"""Daily brief tool."""

from ..brief import daily_brief as build_daily_brief
from . import tool


@tool(
    description="Create Lily's local daily brief: date/time, system status, pending reminders, recent notes, and remembered facts."
)
def daily_brief() -> str:
    return build_daily_brief()
