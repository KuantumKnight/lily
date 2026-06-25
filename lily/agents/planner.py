"""The planner agent — turns a goal into an ordered list of concrete steps.

Routed to when a request looks like planning ("plan my…", "break down…"). It asks
the brain for a numbered list and parses it into clean steps; the parsing is a pure
function so it can be tested without a model. The resulting plan is announced on the
bus as ``plan.created`` for other agents to pick up.
"""

import re

from .. import brain, bus
from ..log import get_logger
from . import Agent, register

log = get_logger("planner")

PLANNER_SYSTEM = (
    "You are Lily's planner. Break the user's goal into a short, ordered list of "
    "concrete, actionable steps. Output ONLY a numbered list (1., 2., 3., ...), one "
    "step per line — no preamble, no commentary, no closing remarks. Aim for 3-7 steps."
)

_NUMBERED = re.compile(r"^(?:step\s*)?\d+[.)\:]\s*(.+)$", re.IGNORECASE)
_BULLET = re.compile(r"^[-*•]\s*(.+)$")


def _parse_steps(text: str) -> list[str]:
    """Extract ordered steps from a model's list. Pure — no I/O."""
    steps: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = _NUMBERED.match(line) or _BULLET.match(line)
        if match:
            steps.append(match.group(1).strip())
    if steps:
        return steps
    # Fallback: no list markers — treat each non-empty line as a step.
    return [line.strip() for line in text.splitlines() if line.strip()]


def plan(goal: str) -> list[str]:
    """Decompose ``goal`` into steps using the brain. Raises BrainOffline on failure."""
    messages = [
        {"role": "system", "content": PLANNER_SYSTEM},
        {"role": "user", "content": goal.strip()},
    ]
    msg = brain.chat_once(messages)
    return _parse_steps((msg.get("content") or "").strip())


def _handle(query: str, messages: list) -> str:
    goal = query.strip()
    steps = plan(goal)
    if not steps:
        return "I couldn't break that down into steps — try rephrasing the goal."
    bus.publish("plan.created", {"goal": goal, "steps": steps})
    log.info("planned %d steps for: %s", len(steps), goal)
    body = "\n".join(f"{i}. {step}" for i, step in enumerate(steps, 1))
    return f"Here's a plan:\n{body}"


register(
    Agent(
        name="planner",
        description="Breaks a goal into ordered, actionable steps.",
        handler=_handle,
        triggers=("plan ", "make a plan", "break down", "step by step", "steps to"),
    )
)
