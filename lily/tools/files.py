"""Desktop-local file creation tools."""

from __future__ import annotations

import os
from pathlib import Path

from . import tool


def _desktop_root() -> Path:
    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        return Path(userprofile) / "Desktop"
    return Path.home() / "Desktop"


def _resolve_desktop_path(path: str) -> Path:
    root = _desktop_root().expanduser().resolve(strict=False)
    candidate = Path(path).expanduser()
    target = candidate if candidate.is_absolute() else root / candidate
    resolved = target.resolve(strict=False)
    if resolved == root or root in resolved.parents:
        return resolved
    raise ValueError(f"path must stay inside the Desktop folder: {resolved}")


@tool(description="Create a local folder on the user's Desktop. Relative paths are created under Desktop.")
def create_desktop_folder(path: str) -> str:
    folder = _resolve_desktop_path(path)
    folder.mkdir(parents=True, exist_ok=True)
    return f"Created folder: {folder}"


@tool(
    description=(
        "Create or overwrite a text file on the user's Desktop. "
        "Relative paths are created under Desktop."
    )
)
def write_desktop_text_file(path: str, content: str, overwrite: bool = False) -> str:
    file_path = _resolve_desktop_path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if file_path.exists() and not overwrite:
        raise FileExistsError(f"{file_path} already exists; set overwrite=true to replace it")
    file_path.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} characters to {file_path}"
