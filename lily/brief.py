"""Daily brief assembly from local Lily state."""

from datetime import datetime

from . import memory
from .tools.notes import list_notes, list_reminders
from .tools.system import system_status


def daily_brief() -> str:
    """Return a compact local-first daily brief."""
    parts = [
        f"# Daily brief\n\nToday is {datetime.now().strftime('%A, %d %B %Y, %H:%M')}.",
        "## System\n" + system_status(),
        "## Pending reminders\n" + list_reminders(limit=8),
        "## Recent notes\n" + list_notes(limit=5),
    ]

    facts = memory.long_term_context(limit=6)
    if facts:
        parts.append("## Long-term memory\n" + facts)
    return "\n\n".join(parts)
