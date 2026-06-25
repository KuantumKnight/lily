"""Git tools — let Lily report what was shipped over a recent window."""

from ..agents import git as git_agent
from . import tool


@tool(description="Summarize what was shipped in the last N days (commits, files, churn). "
                  "days defaults to 7.")
def work_digest(days: int = 7) -> str:
    return git_agent._format(git_agent.digest(days))
