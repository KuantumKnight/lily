"""Opportunity tools — let Lily check your configured RSS/Atom feeds."""

from ..agents import opportunities as opp
from . import tool


@tool(description="List recent opportunities (CFPs, CTFs, etc.) from configured RSS feeds. "
                  "limit defaults to 10.")
def check_opportunities(limit: int = 10) -> str:
    items = opp.opportunities(limit)
    if not items:
        return "No opportunities found (or no feeds configured)."
    return "\n".join(f"• {it.title}" + (f" — {it.link}" if it.link else "") for it in items)
