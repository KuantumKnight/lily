"""Anti-distraction agent."""

import re

from .. import focus
from . import Agent, register


def _handle(query: str, messages: list) -> str:
    lowered = query.lower()
    if "end" in lowered or "stop" in lowered:
        return focus.end()
    minutes = _minutes(query)
    if "status" in lowered:
        return focus.status()
    return focus.negotiate(query, minutes=minutes)


def _minutes(text: str) -> int:
    match = re.search(r"\b(\d{1,3})\s*(min|minute|minutes)\b", text.lower())
    return int(match.group(1)) if match else 25


register(
    Agent(
        name="focus",
        description="Negotiates focus blocks and protects attention from low-priority interruptions.",
        handler=_handle,
        triggers=("focus", "do not disturb", "deep work", "protect my focus", "anti distraction"),
    )
)
