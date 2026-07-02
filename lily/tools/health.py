"""Runtime health diagnostics tool."""

from .. import health
from . import tool


@tool(description="Report local runtime health: required Python packages and external commands.")
def runtime_health() -> str:
    return health.report()
