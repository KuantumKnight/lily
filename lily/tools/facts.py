"""Long-term memory tools for durable facts and preferences."""

from .. import memory
from . import tool


def _format_facts(facts: list[dict]) -> str:
    if not facts:
        return "None found."
    return "\n".join(f"#{fact['id']} [{fact['kind']}]: {fact['content']}" for fact in facts)


@tool(
    description="Save a durable fact or preference about the user. kind should be 'fact', 'preference', or another short label."
)
def remember_fact(content: str, kind: str = "fact") -> str:
    content = content.strip()
    kind = kind.strip() or "fact"
    if not content:
        return "[error] fact content is empty"
    fact_id = memory.remember_fact(content, kind)
    return f"Saved {kind} #{fact_id}."


@tool(description="Search Lily's durable long-term memory facts and preferences.")
def recall_facts(query: str = "", limit: int = 10) -> str:
    return _format_facts(memory.list_facts(limit=limit, query=query))


@tool(description="Delete one durable long-term memory fact by numeric fact_id.")
def forget_fact(fact_id: int) -> str:
    if memory.forget_fact(fact_id):
        return f"Forgot fact #{fact_id}."
    return f"No fact #{fact_id} found."
