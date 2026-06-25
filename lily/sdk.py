"""Public SDK for building Lily agents.

An agent is a named handler the orchestrator can route to, optionally wired into
the event bus. The whole surface you need lives here:

    from lily.sdk import Agent, register, subscribe, publish

    def handle(query, messages):
        return "the weather is lovely"

    register(Agent(
        name="weather",
        description="Answers weather questions.",
        handler=handle,
        triggers=("weather", "forecast"),
    ))

    # react to anything happening in the system
    subscribe("lily.reply", lambda topic, data: print("Lily said:", data["reply"]))

``handler(query, messages)`` returns the reply text. ``triggers`` are lowercase
substrings that route a request to your agent before the default conversation
agent sees it. Published bus events include ``user.message``, ``lily.reply``,
and ``reminder.fired``.
"""

from .agents import Agent, all_agents, get, register, unregister
from .bus import WILDCARD, publish, subscribe, unsubscribe

__all__ = [
    "Agent",
    "register",
    "unregister",
    "get",
    "all_agents",
    "subscribe",
    "unsubscribe",
    "publish",
    "WILDCARD",
]
