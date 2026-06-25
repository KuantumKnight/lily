"""The orchestrator — routes each request to the agent best suited to handle it.

Routing is trigger/keyword based today: cheap, deterministic, and easy to reason
about. :func:`route` is the single seam where smarter (LLM-based) intent
classification can be dropped in without touching callers.
"""

from . import agents
from .log import get_logger

log = get_logger("orchestrator")

DEFAULT_AGENT = "conversation"


def route(query: str) -> "agents.Agent | None":
    """Pick the agent for ``query`` — a trigger match wins, else the default."""
    lowered = query.lower()
    for agent in agents.all_agents():
        if agent.name == DEFAULT_AGENT:
            continue
        if any(trigger in lowered for trigger in agent.triggers):
            return agent
    return agents.get(DEFAULT_AGENT)


def handle(query: str, messages: list) -> str:
    """Route ``query`` to an agent and return its reply."""
    agent = route(query)
    if agent is None:  # roster empty — fall back to the raw engine
        from . import engine

        return engine.converse(messages)
    log.info("routing to agent: %s", agent.name)
    return agent.handler(query, messages)
