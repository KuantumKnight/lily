"""Lily's tool framework — let her call local Python functions.

Decorate a function with ``@tool`` and it becomes callable by Lily. The JSON schema the
model needs is derived automatically from the function signature and docstring.

This is the foundation every future agent plugs into: a "skill" is just a registered tool.
"""

import inspect
from collections.abc import Callable

from ..log import get_logger

log = get_logger("tools")

_REGISTRY: dict[str, dict] = {}

_PY_TO_JSON = {str: "string", int: "integer", float: "number", bool: "boolean"}


def tool(fn: Callable | None = None, *, description: str | None = None):
    """Register a function as a Lily tool. Usable as ``@tool`` or ``@tool(description=...)``."""

    def wrap(f: Callable) -> Callable:
        _REGISTRY[f.__name__] = {"fn": f, "schema": _build_schema(f, description)}
        log.debug("registered tool: %s", f.__name__)
        return f

    return wrap(fn) if callable(fn) else wrap


def _build_schema(f: Callable, description: str | None) -> dict:
    sig = inspect.signature(f)
    props: dict = {}
    required: list[str] = []
    for name, param in sig.parameters.items():
        json_type = _PY_TO_JSON.get(param.annotation, "string")
        props[name] = {"type": json_type}
        if param.default is inspect.Parameter.empty:
            required.append(name)
    return {
        "type": "function",
        "function": {
            "name": f.__name__,
            "description": (description or f.__doc__ or "").strip(),
            "parameters": {"type": "object", "properties": props, "required": required},
        },
    }


def schemas() -> list[dict] | None:
    """All registered tool schemas, ready to pass to the model. None if empty."""
    return [entry["schema"] for entry in _REGISTRY.values()] or None


def execute(name: str, args: dict | None) -> str:
    """Run a tool by name. Never raises — errors come back as text the model can read."""
    entry = _REGISTRY.get(name)
    if entry is None:
        return f"[error] unknown tool '{name}'"
    try:
        result = entry["fn"](**(args or {}))
        return str(result)
    except Exception as exc:  # surface failures to the model, don't crash Lily
        log.error("tool %s failed: %s", name, exc)
        return f"[error] {name} failed: {exc}"


def load_builtins() -> None:
    """Import the modules that register Lily's built-in tools."""
    from . import (  # noqa: F401
        audit,
        brief,
        builtin,
        calendar,
        cloud,
        coordination,
        context,
        decisions,
        dev,
        encryption,
        facts,
        feedback,
        focus,
        git,
        habits,
        mode,
        notes,
        notifications,
        ocr,
        opportunities,
        panic,
        predict,
        projects,
        recall,
        replay,
        resources,
        retrieval,
        screen,
        security,
        stt,
        system,
        timeline,
        tts,
        vision,
    )
