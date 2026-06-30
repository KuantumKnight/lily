"""Panic wipe and unlock tools."""

from .. import panic
from . import tool


@tool(description="Unlock Lily memory by decrypting the configured age-encrypted database.")
def unlock_memory(identity_path: str = "", encrypted_path: str = "") -> str:
    try:
        path = panic.unlock_memory(identity_path=identity_path, encrypted_path=encrypted_path)
    except Exception as exc:
        return f"[error] {exc}"
    return f"Unlocked memory to {path}"


@tool(
    description=(
        "Permanently delete Lily's local runtime memory after exact confirmation. "
        "confirm must be WIPE LILY MEMORY. Keeps encrypted backup by default."
    )
)
def panic_wipe(confirm: str, keep_encrypted: bool = True) -> str:
    try:
        deleted = panic.panic_wipe(confirm=confirm, keep_encrypted=keep_encrypted)
    except panic.PanicRefused as exc:
        return f"[error] {exc}"
    return "Deleted:\n" + "\n".join(deleted) if deleted else "No runtime memory files existed."
