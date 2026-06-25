"""Minimal iCalendar (.ics) reader — stdlib only, no third-party deps.

Parses just enough of RFC 5545 to be useful: VEVENT blocks with DTSTART/DTEND/SUMMARY/
LOCATION, line unfolding, and the common date-time forms (UTC ``Z``, floating local, and
all-day ``VALUE=DATE``). Everything here is pure and testable from a string — fetching
the file lives in the calendar agent. :func:`upcoming_events`, :func:`find_conflicts`,
and :func:`event_prep_times` operate on parsed :class:`Event` lists.
"""

import datetime as _dt
from dataclasses import dataclass

from .log import get_logger

log = get_logger("calendar")


@dataclass
class Event:
    summary: str
    start: _dt.datetime
    end: _dt.datetime | None
    location: str = ""

    def __str__(self) -> str:
        when = self.start.strftime("%a %d %b %H:%M")
        loc = f" @ {self.location}" if self.location else ""
        return f"{self.summary} — {when}{loc}"


def _unfold(text: str) -> list[str]:
    """Join RFC 5545 continuation lines (those beginning with space or tab)."""
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def _parse_dt(value: str) -> _dt.datetime | None:
    """Parse an iCal date/date-time value into a (naive) datetime. None if unparseable."""
    value = value.strip()
    try:
        if value.endswith("Z"):
            return _dt.datetime.strptime(value, "%Y%m%dT%H%M%SZ")
        if "T" in value:
            return _dt.datetime.strptime(value, "%Y%m%dT%H%M%S")
        return _dt.datetime.strptime(value, "%Y%m%d")  # all-day
    except ValueError:
        return None


def parse_ics(text: str) -> list[Event]:
    """Parse all VEVENTs from ICS ``text`` into Events, sorted by start. Pure."""
    events: list[Event] = []
    cur: dict | None = None
    for line in _unfold(text):
        if line == "BEGIN:VEVENT":
            cur = {}
            continue
        if line == "END:VEVENT":
            if cur and cur.get("start"):
                events.append(
                    Event(
                        summary=cur.get("summary", "(untitled)"),
                        start=cur["start"],
                        end=cur.get("end"),
                        location=cur.get("location", ""),
                    )
                )
            cur = None
            continue
        if cur is None or ":" not in line:
            continue
        name, _, val = line.partition(":")
        key = name.split(";", 1)[0].upper()  # drop params like ;TZID=...
        if key == "SUMMARY":
            cur["summary"] = val.strip()
        elif key == "LOCATION":
            cur["location"] = val.strip()
        elif key == "DTSTART":
            cur["start"] = _parse_dt(val)
        elif key == "DTEND":
            cur["end"] = _parse_dt(val)
    return sorted([e for e in events if e.start], key=lambda e: e.start)


def upcoming_events(events: list[Event], now: _dt.datetime, within_hours: int = 24) -> list[Event]:
    """Events starting between ``now`` and ``now + within_hours``. Pure."""
    horizon = now + _dt.timedelta(hours=within_hours)
    return [e for e in events if now <= e.start <= horizon]


def find_conflicts(events: list[Event]) -> list[tuple[Event, Event]]:
    """Pairs of events whose times overlap. Needs DTEND to detect overlap. Pure."""
    timed = sorted([e for e in events if e.end], key=lambda e: e.start)
    conflicts: list[tuple[Event, Event]] = []
    for i, a in enumerate(timed):
        for b in timed[i + 1:]:
            if b.start >= a.end:
                break  # sorted by start — nothing later can overlap a
            conflicts.append((a, b))
    return conflicts


def event_prep_times(events: list[Event], prep_minutes: int) -> list[tuple[Event, _dt.datetime]]:
    """For each event, the moment Lily should prompt prep (start - prep_minutes). Pure."""
    delta = _dt.timedelta(minutes=prep_minutes)
    return [(e, e.start - delta) for e in events]
