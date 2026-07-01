"""Multi-agent goal coordination."""

from . import agents, bus


SKIP = {"conversation", "coordinator"}


def coordinate(goal: str, agent_names: str = "", messages: list | None = None) -> str:
    """Ask multiple specialized agents to collaborate on one goal."""
    selected = _select(goal, agent_names)
    if not selected:
        return "No specialized agents matched that goal."

    results = []
    base_messages = messages or [{"role": "user", "content": goal}]
    for agent in selected:
        try:
            reply = agent.handler(goal, base_messages)
        except Exception as exc:
            reply = f"[error] {exc}"
        results.append({"agent": agent.name, "reply": reply})

    bus.publish("agents.coordinated", {"goal": goal, "agents": [a.name for a in selected]})
    return _format(goal, results)


def _select(goal: str, agent_names: str) -> list[agents.Agent]:
    requested = [name.strip() for name in agent_names.split(",") if name.strip()]
    if requested:
        return [
            agent for name in requested
            if (agent := agents.get(name)) is not None and agent.name not in SKIP
        ]

    lowered = goal.lower()
    matches = []
    for agent in agents.all_agents():
        if agent.name in SKIP:
            continue
        if any(trigger in lowered for trigger in agent.triggers):
            matches.append(agent)
    return matches[:4]


def _format(goal: str, results: list[dict]) -> str:
    lines = [f"Coordinated goal: {goal}"]
    for result in results:
        lines.append(f"\n[{result['agent']}]\n{result['reply']}")
    return "\n".join(lines)
