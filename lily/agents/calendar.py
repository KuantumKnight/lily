"""The calendar agent — reads a local .ics file and reports what's coming up.

Disabled until ``calendar_ics_path`` points at a file (personal, local-only — Lily
never reaches out to a calendar service). It loads + parses the file with the stdlib
reader in :mod:`lily.calendar`, then surfaces the next day's events and any overlaps.
Announces ``calendar.upcoming`` on the bus.
"""

import datetime as _dt
from pathlib import Path

from .. import bus
from .. import calendar as cal
from ..config import CALENDAR_ICS_PATH, CALENDAR_PREP_MINUTES
from ..log import get_logger
from . import Agent, register

log = get_logger("calendar-agent")


def _load() -> list[cal.Event]:
    path = (CALENDAR_ICS_PATH or "").strip()
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        log.warning("calendar file not found: %s", path)
        return []
    try:
        return cal.parse_ics(p.read_text(encoding="utf-8", errors="replace"))
    except OSError as exc:
        log.warning("calendar read failed: %s", exc)
        return []


def _handle(query: str, messages: list) -> str:
    if not (CALENDAR_ICS_PATH or "").strip():
        return "No calendar is configured. Set calendar_ics_path to a .ics file to enable this."
    events = _load()
    if not events:
        return "Your calendar is empty (or unreadable)."
    now = _dt.datetime.now()
    upcoming = cal.upcoming_events(events, now, within_hours=24)
    conflicts = cal.find_conflicts(upcoming)
    bus.publish("calendar.upcoming", {"count": len(upcoming), "conflicts": len(conflicts)})

    if not upcoming:
        return "Nothing on your calendar in the next 24 hours."
    lines = [f"Next 24h ({len(upcoming)} event{'s' if len(upcoming) != 1 else ''}):"]
    lines += [f"  • {e}" for e in upcoming]
    if conflicts:
        lines.append(f"\n⚠ {len(conflicts)} scheduling conflict(s):")
        lines += [f"  • {a.summary} overlaps {b.summary}" for a, b in conflicts]
    lines.append(f"\n(I'll suggest prepping {CALENDAR_PREP_MINUTES} min ahead.)")
    return "\n".join(lines)


register(
    Agent(
        name="calendar",
        description="Reads your local calendar and flags what's coming up and any conflicts.",
        handler=_handle,
        triggers=("my calendar", "what's on", "whats on", "upcoming events", "my schedule", "agenda"),
    )
)
