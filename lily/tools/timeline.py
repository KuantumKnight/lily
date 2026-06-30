"""Timeline tools — append and inspect chronological life events."""

from .. import timeline
from . import tool


@tool(description="Append a chronological timeline event. Existing events are never changed.")
def record_timeline_event(kind: str, title: str, content: str = "") -> str:
    event_id = timeline.append_event(kind=kind, title=title, content=content)
    return f"Recorded timeline event #{event_id}."


@tool(description="Show recent timeline events, newest first.")
def recent_timeline(limit: int = 20) -> str:
    return timeline.format_events(timeline.recent(limit))


@tool(description="Keyword search the timeline by title, content, or kind.")
def search_timeline(query: str, limit: int = 20) -> str:
    return timeline.format_events(timeline.search(query, limit))
