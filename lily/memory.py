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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS facts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            created_ts REAL NOT NULL,
            kind       TEXT NOT NULL,
            content    TEXT NOT NULL
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


def remember_fact(content: str, kind: str = "fact") -> int:
    """Persist a durable user fact or preference."""
    conn = _conn()
    with conn:
        cur = conn.execute(
            "INSERT INTO facts (created_ts, kind, content) VALUES (?, ?, ?)",
            (time.time(), kind.strip() or "fact", content.strip()),
        )
    conn.close()
    return int(cur.lastrowid)


def list_facts(limit: int = 20, query: str = "") -> list[dict]:
    """Return durable facts, newest first, optionally filtered by text."""
    limit = max(1, min(int(limit), 100))
    conn = _conn()
    conn.row_factory = sqlite3.Row
    if query.strip():
        rows = conn.execute(
            """
            SELECT id, kind, content
            FROM facts
            WHERE content LIKE ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (f"%{query.strip()}%", limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, kind, content FROM facts ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def forget_fact(fact_id: int) -> bool:
    """Delete one durable fact by id."""
    conn = _conn()
    with conn:
        cur = conn.execute("DELETE FROM facts WHERE id = ?", (int(fact_id),))
    conn.close()
    return cur.rowcount > 0


def long_term_context(limit: int = 12) -> str:
    """Compact facts block for the system prompt."""
    facts = list_facts(limit=limit)
    if not facts:
        return ""

    lines = ["Long-term memory facts and preferences:"]
    for fact in reversed(facts):
        lines.append(f"- [{fact['kind']}] {fact['content']}")
    return "\n".join(lines)
