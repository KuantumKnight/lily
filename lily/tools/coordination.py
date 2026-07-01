"""Multi-agent coordination tools."""

from .. import coordination
from . import tool


@tool(description="Coordinate multiple specialized agents on one goal. agent_names is comma-separated and optional.")
def coordinate_agents(goal: str, agent_names: str = "") -> str:
    return coordination.coordinate(goal=goal, agent_names=agent_names)
