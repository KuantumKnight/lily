"""Dev tools — let Lily inspect the repo and run its tests on demand."""

from .. import devtools
from . import tool


@tool(description="Show the git working-tree status (branch + changed files).")
def git_status() -> str:
    return devtools.git_status()


@tool(description="Show the most recent git commits. count defaults to 5 (max 50).")
def git_log(count: int = 5) -> str:
    return devtools.git_log(count)


@tool(description="Run the project's test suite (pytest). target optionally scopes it, "
                  "e.g. a path or '-k name'. Returns the result and any failures.")
def run_tests(target: str = "") -> str:
    rc, output = devtools.run_tests(target)
    status = "passed" if rc == 0 and not devtools.detect_failure(output) else f"failed (exit {rc})"
    return f"Tests {status}.\n\n{output[-3000:]}"
