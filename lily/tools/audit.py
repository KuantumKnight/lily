"""Audit-log tools."""

from .. import audit
from . import tool


@tool(description="Show recent per-agent access audit entries.")
def recent_audit(limit: int = 50, agent: str = "") -> str:
    return audit.format_rows(audit.recent(limit=limit, agent=agent))
