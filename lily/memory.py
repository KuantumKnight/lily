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
    # Layer 2 — project memory: notes scoped to a named project, plus a tiny
    # key/value store for app state (e.g. which project is active).
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS state (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_notes (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ts      REAL NOT NULL,
            project TEXT NOT NULL,
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


# --- Layer 2: project memory -------------------------------------------------


def set_state(key: str, value: str) -> None:
    """Set (or clear, if value is empty) a key in the small app-state store."""
    conn = _conn()
    with conn:
        if value:
            conn.execute(
                "INSERT INTO state (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
        else:
            conn.execute("DELETE FROM state WHERE key = ?", (key,))
    conn.close()


def get_state(key: str, default: str = "") -> str:
    conn = _conn()
    row = conn.execute("SELECT value FROM state WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row[0] if row else default


def set_active_project(name: str) -> None:
    """Make ``name`` the active project (empty string clears it)."""
    set_state("active_project", name.strip())


def active_project() -> str:
    return get_state("active_project", "")


def add_project_note(project: str, content: str) -> int:
    """Attach a note to a project. Returns the note id."""
    project = project.strip()
    content = content.strip()
    if not project or not content:
        raise ValueError("project and content are required")
    conn = _conn()
    with conn:
        cur = conn.execute(
            "INSERT INTO project_notes (ts, project, content) VALUES (?, ?, ?)",
            (time.time(), project, content),
        )
    conn.close()
    return int(cur.lastrowid)


def project_notes(project: str, limit: int = 20) -> list[dict]:
    """Return a project's notes, newest first."""
    limit = max(1, min(int(limit), 100))
    conn = _conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, ts, content FROM project_notes WHERE project = ? ORDER BY id DESC LIMIT ?",
        (project.strip(), limit),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def list_projects() -> list[str]:
    """All projects that have notes, most-recently-touched first."""
    conn = _conn()
    rows = conn.execute(
        "SELECT project FROM project_notes GROUP BY project ORDER BY MAX(ts) DESC"
    ).fetchall()
    conn.close()
    return [row[0] for row in rows]


def project_context(limit: int = 8) -> str:
    """Compact notes block for the active project, for the system prompt."""
    project = active_project()
    if not project:
        return ""
    notes = project_notes(project, limit=limit)
    lines = [f"Active project: {project}."]
    for note in reversed(notes):
        lines.append(f"- {note['content']}")
    return "\n".join(lines)
