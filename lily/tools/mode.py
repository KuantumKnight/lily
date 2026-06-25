"""Mode tools — let Lily check and switch her own attention mode."""

from .. import mode as mode_module
from . import tool


@tool(description="Report Lily's current attention mode (passive or active).")
def get_mode() -> str:
    return f"Lily is in {mode_module.current()} mode."


@tool(description="Switch Lily's attention mode. mode_name must be 'passive' or 'active'.")
def set_mode(mode_name: str) -> str:
    if mode_module.set_mode(mode_name, reason="tool"):
        return f"Switched to {mode_module.current()} mode."
    if mode_name.strip().lower() not in {"passive", "active"}:
        return "[error] mode must be 'passive' or 'active'."
    return f"Already in {mode_module.current()} mode."
