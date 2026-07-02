"""Lily's agent layer — specialized handlers the orchestrator routes intents to.

An *agent* is a named handler with a description and optional trigger keywords. The
orchestrator (``lily.orchestrator``) picks one per request; everything that isn't a
specialized agent falls through to the default ``conversation`` agent.

This module is the registration SDK other features build on: ``register`` an
:class:`Agent`, give it ``triggers`` for fast routing, and it joins the roster.
"""

import importlib
from collections.abc import Callable
from dataclasses import dataclass, field

from ..log import get_logger

log = get_logger("agents")

# handler signature: (query, messages) -> reply text
Handler = Callable[[str, list], str]

_REGISTRY: dict[str, "Agent"] = {}


@dataclass
class Agent:
    """A routable capability. ``triggers`` are lowercase substrings that select it."""

    name: str
    description: str
    handler: Handler
    triggers: tuple[str, ...] = field(default_factory=tuple)


def register(agent: Agent) -> Agent:
    """Add (or replace) an agent in the roster. Returns it for convenience."""
    _REGISTRY[agent.name] = agent
    log.debug("registered agent: %s", agent.name)
    return agent


def unregister(name: str) -> None:
    _REGISTRY.pop(name, None)


def get(name: str) -> "Agent | None":
    return _REGISTRY.get(name)


def all_agents() -> list["Agent"]:
    return list(_REGISTRY.values())


_BUILTIN_MODULES = (
    "calendar",
    "conversation",
    "coordinator",
    "dev",
    "focus",
    "git",
    "opportunities",
    "planner",
    "predict",
)


def load_builtins() -> None:
    """Import modules that register Lily's built-in agents."""
    for name in _BUILTIN_MODULES:
        try:
            importlib.import_module(f"{__name__}.{name}")
        except ImportError as exc:
            log.warning("skipped agent module %s: %s", name, exc)
