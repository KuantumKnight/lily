"""Project memory tools — scope notes to whatever the user is working on."""

from .. import memory
from . import tool


@tool(description="Set the active project Lily should scope notes and context to.")
def set_project(name: str) -> str:
    name = name.strip()
    if not name:
        return "[error] project name is empty"
    memory.set_active_project(name)
    return f"Active project is now '{name}'."


@tool(description="Show which project is currently active.")
def current_project() -> str:
    project = memory.active_project()
    return f"Active project: {project}." if project else "No active project."


@tool(description="Save a note to the active project's memory.")
def note_project(content: str) -> str:
    project = memory.active_project()
    if not project:
        return "[error] no active project — set one first with set_project."
    note_id = memory.add_project_note(project, content)
    return f"Noted in '{project}' (#{note_id})."


@tool(description="Recall the active project's notes, newest first.")
def recall_project(limit: int = 10) -> str:
    project = memory.active_project()
    if not project:
        return "No active project."
    notes = memory.project_notes(project, limit=limit)
    if not notes:
        return f"No notes yet for '{project}'."
    body = "\n".join(f"#{n['id']}: {n['content']}" for n in notes)
    return f"Notes for '{project}':\n{body}"


@tool(description="List all projects Lily has notes for.")
def list_projects() -> str:
    projects = memory.list_projects()
    return "\n".join(f"- {p}" for p in projects) if projects else "No projects yet."
