"""The orchestrator — routes each request to the agent best suited to handle it.

Routing is trigger/keyword based today: cheap, deterministic, and easy to reason
about. :func:`route` is the single seam where smarter (LLM-based) intent
classification can be dropped in without touching callers.
"""

from . import agents, audit, bus, timeline
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
    """Route ``query`` to an agent and return its reply, announcing both on the bus."""
    bus.publish("user.message", {"query": query})
    timeline.append_event("user", "User message", query)
    agent = route(query)
    if agent is None:  # roster empty — fall back to the raw engine
        from . import engine

        audit.record("engine", "handle", "conversation", query[:500])
        reply = engine.converse(messages)
        bus.publish("lily.reply", {"query": query, "agent": None, "reply": reply})
        timeline.append_event("assistant", "Lily reply", reply, {"agent": None})
        audit.record("engine", "reply", "conversation", reply[:500])
        return reply
    log.info("routing to agent: %s", agent.name)
    audit.record(agent.name, "handle", "conversation", query[:500])
    reply = agent.handler(query, messages)
    bus.publish("lily.reply", {"query": query, "agent": agent.name, "reply": reply})
    timeline.append_event("assistant", "Lily reply", reply, {"agent": agent.name})
    audit.record(agent.name, "reply", "conversation", reply[:500])
    return reply
