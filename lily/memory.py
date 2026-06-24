"""Conversation memory — a simple, durable SQLite log of what was said.

This is Layer 1 (conversation memory) of Lily's memory architecture. Later versions add
project, behavior, and timeline layers on top of the same database.
"""

import sqlite3
import time

from .config import DB_PATH


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ts      REAL NOT NULL,
            role    TEXT NOT NULL,   -- 'user' | 'assistant'
            content TEXT NOT NULL
        )
        """
    )
    return conn


def remember(role: str, content: str) -> None:
    """Persist one message."""
    conn = _conn()
    with conn:
        conn.execute(
            "INSERT INTO messages (ts, role, content) VALUES (?, ?, ?)",
            (time.time(), role, content),
        )
    conn.close()


def recent(limit: int) -> list[dict]:
    """Return the last `limit` messages, oldest-first, ready for the chat API."""
    conn = _conn()
    rows = conn.execute(
        "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [{"role": role, "content": content} for role, content in reversed(rows)]


def forget_all() -> None:
    """Wipe conversation memory (useful for a fresh start)."""
    conn = _conn()
    with conn:
        conn.execute("DELETE FROM messages")
    conn.close()
