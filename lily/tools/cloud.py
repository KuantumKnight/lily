"""Cloud-burst reasoning tools."""

from .. import cloud
from . import tool


@tool(
    description=(
        "Escalate only a hard query to the configured opt-in frontier API. "
        "Cloud burst must be enabled in config and API key env must be set."
    )
)
def cloud_burst(query: str, context: str = "", force: bool = False) -> str:
    try:
        return cloud.ask(query=query, context=context, force=force)
    except cloud.CloudBurstUnavailable as exc:
        return f"[error] {exc}"


@tool(description="Check whether a query is hard enough for cloud-burst reasoning.")
def cloud_burst_check(query: str) -> str:
    return "hard" if cloud.is_hard(query) else "local"
