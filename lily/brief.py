"""Daily brief assembly from local Lily state."""

from datetime import datetime

from . import goals, memory
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

    goal = goals.active_goal()
    if goal:
        goal_lines = [
            f"**{goal['title']}** - {goal['progress']}% complete ({goal['status']})"
        ]
        if goal["next_action"]:
            goal_lines.append(f"Next action: {goal['next_action']}")
        if goal["blocker"]:
            goal_lines.append(f"Blocker: {goal['blocker']}")
        if goal["task_summary"]["remaining"]:
            goal_lines.append(f"Remaining tasks: {goal['task_summary']['remaining']}")
        parts.insert(1, "## Active goal\n" + "\n".join(goal_lines))

    facts = memory.long_term_context(limit=6)
    if facts:
        parts.append("## Long-term memory\n" + facts)
    return "\n\n".join(parts)
