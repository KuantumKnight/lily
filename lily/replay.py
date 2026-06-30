"""Life replay queries over Lily's timeline."""

from datetime import date, datetime, time as dt_time, timedelta
import re

from . import timeline


_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def replay(query: str, limit: int = 100) -> str:
    """Answer a natural-ish time query by replaying timeline events."""
    start, end, label = parse_window(query)
    events = timeline.between(start.timestamp(), end.timestamp(), limit=limit)
    if not events:
        return f"No timeline events found for {label}."
    return f"Timeline for {label}:\n{timeline.format_events(events)}"


def parse_window(query: str) -> tuple[datetime, datetime, str]:
    """Parse common local date phrases into a half-open day window."""
    lowered = query.lower().strip()
    day = _parse_iso_date(lowered) or _parse_relative_day(lowered) or _parse_weekday(lowered)
    if day is None:
        day = date.today()
    start = datetime.combine(day, dt_time.min)
    end = start + timedelta(days=1)
    return start, end, day.strftime("%A, %Y-%m-%d")


def _parse_iso_date(text: str) -> date | None:
    match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def _parse_relative_day(text: str) -> date | None:
    today = date.today()
    if "today" in text:
        return today
    if "yesterday" in text:
        return today - timedelta(days=1)
    return None


def _parse_weekday(text: str) -> date | None:
    today = date.today()
    for name, index in _WEEKDAYS.items():
        if name not in text:
            continue
        delta = (today.weekday() - index) % 7
        if delta == 0 or f"last {name}" in text:
            delta = 7 if delta == 0 else delta
        return today - timedelta(days=delta)
    return None
