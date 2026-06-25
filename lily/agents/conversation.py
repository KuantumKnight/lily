"""The default conversation agent — general chat and local tool use.

Everything the orchestrator doesn't route elsewhere lands here. It simply drives
the existing think → call tools → think engine, so Lily's baseline behavior is
unchanged; specialized agents layer on top.
"""

from .. import engine
from . import Agent, register


def _handle(query: str, messages: list) -> str:
    return engine.converse(messages)


register(
    Agent(
        name="conversation",
        description="General conversation, questions, and local tool use. Lily's default.",
        handler=_handle,
    )
)
