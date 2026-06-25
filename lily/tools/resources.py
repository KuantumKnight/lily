"""Resource tools — inspect and manage Lily's loaded models."""

from .. import resource_manager
from . import tool


@tool(description="Show which heavy models (stt, tts, wake) are currently loaded in memory.")
def resource_status() -> str:
    status = resource_manager.status()
    return ", ".join(f"{name}: {'loaded' if loaded else 'free'}" for name, loaded in status.items())


@tool(description="Unload heavy models to free memory. model can be 'stt', 'tts', 'wake', or 'all'.")
def unload_model(model: str = "all") -> str:
    model = model.strip().lower()
    if model == "all":
        freed = resource_manager.unload_all()
        return f"Freed: {', '.join(freed)}." if freed else "Nothing was loaded."
    return resource_manager.unload(model)
