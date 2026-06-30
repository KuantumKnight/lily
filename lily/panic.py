"""Panic wipe and local memory unlock controls."""

from pathlib import Path

from . import encryption
from .config import DATA_DIR, DB_PATH, ENCRYPTED_DB_PATH

CONFIRM_PHRASE = "WIPE LILY MEMORY"


class PanicRefused(RuntimeError):
    """Raised when a destructive panic operation is not explicitly confirmed."""


def unlock_memory(identity_path: str = "", encrypted_path: str = "") -> Path:
    """Decrypt encrypted memory using a local age identity file."""
    if identity_path:
        from . import config

        config.AGE_IDENTITY = identity_path
        encryption.AGE_IDENTITY = identity_path
    return encryption.decrypt_memory(input_path=encrypted_path)


def panic_wipe(confirm: str, keep_encrypted: bool = True) -> list[str]:
    """Delete local runtime memory files after exact confirmation."""
    if confirm != CONFIRM_PHRASE:
        raise PanicRefused(f"confirmation must exactly equal {CONFIRM_PHRASE!r}")

    deleted: list[str] = []
    targets = [DB_PATH, DATA_DIR / "lily.log"]
    if not keep_encrypted:
        targets.append(ENCRYPTED_DB_PATH)
    targets.extend(_runtime_artifacts())

    for path in targets:
        if path.exists() and path.is_file():
            path.unlink()
            deleted.append(str(path))
    return deleted


def _runtime_artifacts() -> list[Path]:
    paths: list[Path] = []
    for folder in (DATA_DIR / "screenshots",):
        if folder.exists():
            paths.extend(path for path in folder.rglob("*") if path.is_file())
    return paths
