"""Calendar tools — let Lily read the local .ics calendar."""

import datetime as _dt

from .. import calendar as cal
from ..agents import calendar as cal_agent
from . import tool


@tool(description="List calendar events in the next N hours (default 24). "
                  "Requires calendar_ics_path to be configured.")
def upcoming_events(hours: int = 24) -> str:
    events = cal_agent._load()
    if not events:
        return "No calendar configured or no events found."
    upcoming = cal.upcoming_events(events, _dt.datetime.now(), within_hours=max(1, hours))
    if not upcoming:
        return f"Nothing scheduled in the next {hours} hours."
    return "\n".join(f"• {e}" for e in upcoming)


@tool(description="List overlapping (conflicting) calendar events.")
def calendar_conflicts() -> str:
    events = cal_agent._load()
    conflicts = cal.find_conflicts(events)
    if not conflicts:
        return "No scheduling conflicts found."
    return "\n".join(f"• {a.summary} overlaps {b.summary}" for a, b in conflicts)
