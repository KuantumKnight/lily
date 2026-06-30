"""Life replay tools."""

from .. import replay
from . import tool


@tool(
    description=(
        "Replay what was happening during a local date window from Lily's timeline. "
        "Handles phrases like 'last Thursday', 'yesterday', 'today', or '2026-06-30'."
    )
)
def life_replay(query: str, limit: int = 100) -> str:
    return replay.replay(query, limit=limit)
