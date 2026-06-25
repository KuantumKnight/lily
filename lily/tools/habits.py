"""Behavior memory tools — let Lily report the habits she's learned."""

from .. import memory
from . import tool


@tool(description="Report the user's typical active hours, learned from when they interact.")
def work_hours() -> str:
    window = memory.work_hours()
    if window is None:
        return "Not enough activity yet to know your work hours."
    lo, hi = window
    return f"You're usually active between {memory._fmt_hour(lo)} and {memory._fmt_hour(hi)}."


@tool(description="Summarize the user's habits (active hours and busiest day).")
def my_habits() -> str:
    summary = memory.behavior_summary()
    return summary or "I haven't learned your habits yet — give it a little time."
