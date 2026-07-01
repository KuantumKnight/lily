"""Coordinator agent."""

from .. import coordination
from . import Agent, register


def _handle(query: str, messages: list) -> str:
    return coordination.coordinate(query, messages=messages)


register(
    Agent(
        name="coordinator",
        description="Coordinates multiple specialized agents on one goal.",
        handler=_handle,
        triggers=("coordinate", "agents collaborate", "multi-agent", "work together"),
    )
)
