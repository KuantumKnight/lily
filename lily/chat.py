"""Shared conversation service for Lily's CLI and dashboard."""

from . import agents, memory, orchestrator, tools
from .config import CONTEXT_WINDOW
from .persona import PERSONA


def prepare() -> None:
    """Load the capabilities needed for a conversation.

    Registration is idempotent, so this is safe for every entry point.  Keeping it
    here prevents the dashboard from looking healthy while silently running with an
    empty agent/tool roster.
    """
    tools.load_builtins()
    agents.load_builtins()


def build_context(user_input: str) -> list[dict]:
    """Persist a user turn and build the model-ready conversation context."""
    text = user_input.strip()
    if not text:
        raise ValueError("message cannot be empty")

    memory.remember("user", text)
    memory.record_activity("message")
    system_prompt = PERSONA
    for context in (
        memory.long_term_context(),
        memory.project_context(),
        memory.behavior_summary(),
    ):
        if context:
            system_prompt = f"{system_prompt}\n\n{context}"
    return [
        {"role": "system", "content": system_prompt},
        *memory.recent(CONTEXT_WINDOW),
    ]


def respond(user_input: str) -> str:
    """Run one complete Lily turn and persist the reply."""
    prepare()
    text = user_input.strip()
    messages = build_context(text)
    reply = orchestrator.handle(text, messages)
    memory.remember("assistant", reply)
    return reply
