"""Encrypted memory-at-rest helpers using the age CLI."""

import shutil
import subprocess
from pathlib import Path

from .config import AGE_IDENTITY, AGE_RECIPIENT, DB_PATH, ENCRYPTED_DB_PATH


class EncryptionUnavailable(RuntimeError):
    """Raised when encryption is not configured or age is unavailable."""


def status() -> str:
    age = shutil.which("age")
    age_keygen = shutil.which("age-keygen")
    parts = [
        f"age: {'available' if age else 'missing'}",
        f"age-keygen: {'available' if age_keygen else 'missing'}",
        f"recipient: {'configured' if AGE_RECIPIENT else 'missing'}",
        f"identity: {'configured' if AGE_IDENTITY else 'missing'}",
        f"encrypted db: {ENCRYPTED_DB_PATH}",
    ]
    return "\n".join(parts)


def encrypt_memory(output_path: str = "") -> Path:
    """Encrypt Lily's SQLite memory DB to an age file."""
    age = _age()
    if not AGE_RECIPIENT:
        raise EncryptionUnavailable("set LILY_AGE_RECIPIENT or age_recipient first")
    if not DB_PATH.exists():
        raise EncryptionUnavailable(f"memory database does not exist: {DB_PATH}")
    out = Path(output_path).expanduser() if output_path else ENCRYPTED_DB_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    _run([age, "-r", AGE_RECIPIENT, "-o", str(out), str(DB_PATH)])
    return out


def decrypt_memory(input_path: str = "", output_path: str = "") -> Path:
    """Decrypt an age memory DB file back to a SQLite DB path."""
    age = _age()
    if not AGE_IDENTITY:
        raise EncryptionUnavailable("set LILY_AGE_IDENTITY or age_identity first")
    identity = Path(AGE_IDENTITY).expanduser()
    if not identity.exists():
        raise EncryptionUnavailable(f"age identity file not found: {identity}")
    src = Path(input_path).expanduser() if input_path else ENCRYPTED_DB_PATH
    if not src.exists():
        raise EncryptionUnavailable(f"encrypted database not found: {src}")
    out = Path(output_path).expanduser() if output_path else DB_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    _run([age, "-d", "-i", str(identity), "-o", str(out), str(src)])
    return out


def _age() -> str:
    exe = shutil.which("age")
    if not exe:
        raise EncryptionUnavailable("age is not installed or not on PATH")
    return exe


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise EncryptionUnavailable((proc.stderr or proc.stdout or "age failed").strip())
