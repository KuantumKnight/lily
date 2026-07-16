"""Goal Engine tools exposed to Lily's local model."""

from .. import goals
from . import tool


@tool(description="Create a persisted goal and make it the active goal.")
def create_goal(
    title: str,
    outcome: str = "",
    success_criteria: str = "",
    priority: int = 3,
    due_at: str = "",
    next_action: str = "",
) -> str:
    goal = goals.create_goal(
        title,
        outcome=outcome,
        success_criteria=success_criteria,
        priority=priority,
        due_at=due_at,
        next_action=next_action,
    )
    return f"Created active goal #{goal['id']}: {goal['title']}."


@tool(description="Show the active goal, progress, next action, and blockers.")
def current_goal() -> str:
    goal = goals.active_goal()
    if not goal:
        return "No active goal."
    lines = [f"Active goal #{goal['id']}: {goal['title']} ({goal['progress']}%)."]
    if goal["next_action"]:
        lines.append(f"Next action: {goal['next_action']}")
    if goal["blocker"]:
        lines.append(f"Blocker: {goal['blocker']}")
    lines.append(
        f"Tasks: {goal['task_summary']['done']}/{goal['task_summary']['total']} complete."
    )
    return "\n".join(lines)


@tool(description="List goals with their ids, status, and progress.")
def list_goals(status: str = "") -> str:
    items = goals.list_goals(status=status, limit=20)
    if not items:
        return "No goals found."
    return "\n".join(
        f"#{item['id']} [{item['status']}] {item['title']} - {item['progress']}%"
        for item in items
    )


@tool(description="Add a concrete task to a persisted goal.")
def add_goal_task(goal_id: int, title: str, assignee: str = "") -> str:
    task = goals.add_task(goal_id, title, assignee=assignee)
    return f"Added task #{task['id']} to goal #{goal_id}: {task['title']}."


@tool(description="Update a goal status: planned, active, paused, blocked, completed, or cancelled.")
def set_goal_status(goal_id: int, status: str, blocker: str = "") -> str:
    changes = {"status": status}
    if blocker or status != "blocked":
        changes["blocker"] = blocker
    goal = goals.update_goal(goal_id, **changes)
    return f"Goal #{goal_id} is now {goal['status']}."


@tool(description="Mark a goal task done or return it to the todo state.")
def set_goal_task_done(goal_id: int, task_id: int, done: bool = True) -> str:
    task = goals.update_task(goal_id, task_id, status="done" if done else "todo")
    return f"Task #{task_id} is now {task['status']}."
