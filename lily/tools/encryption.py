"""Encrypted memory-at-rest tools."""

from .. import encryption
from . import tool


@tool(description="Show local age encryption setup for Lily's memory database.")
def memory_encryption_status() -> str:
    return encryption.status()


@tool(description="Encrypt Lily's SQLite memory database to an age file.")
def encrypt_memory(output_path: str = "") -> str:
    try:
        path = encryption.encrypt_memory(output_path)
    except encryption.EncryptionUnavailable as exc:
        return f"[error] {exc}"
    return f"Encrypted memory to {path}"


@tool(description="Decrypt Lily's age-encrypted memory database with the configured identity file.")
def decrypt_memory(input_path: str = "", output_path: str = "") -> str:
    try:
        path = encryption.decrypt_memory(input_path, output_path)
    except encryption.EncryptionUnavailable as exc:
        return f"[error] {exc}"
    return f"Decrypted memory to {path}"
