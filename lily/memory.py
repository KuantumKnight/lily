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
    # Layer 3 — behavior memory: a timestamped log of when the user interacts,
    # from which Lily infers habits (typical active hours, busiest day).
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS activity (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            ts   REAL NOT NULL,
            kind TEXT NOT NULL
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


# --- Layer 3: behavior memory ------------------------------------------------

_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def record_activity(kind: str = "message", ts: float | None = None) -> None:
    """Log one interaction so Lily can learn the user's rhythms."""
    conn = _conn()
    with conn:
        conn.execute(
            "INSERT INTO activity (ts, kind) VALUES (?, ?)",
            (time.time() if ts is None else ts, kind.strip() or "message"),
        )
    conn.close()


def _activity_timestamps() -> list[float]:
    conn = _conn()
    rows = conn.execute("SELECT ts FROM activity").fetchall()
    conn.close()
    return [row[0] for row in rows]


def work_hours(min_samples: int = 8) -> tuple[int, int] | None:
    """Infer the user's typical active window as (start_hour, end_hour), 0–23.

    Uses the 10th/90th percentile of activity hours so a couple of odd-hour
    sessions don't widen the window. Returns None below ``min_samples``.
    """
    hours = sorted(time.localtime(ts).tm_hour for ts in _activity_timestamps())
    if len(hours) < min_samples:
        return None
    lo = hours[int(0.1 * len(hours))]
    hi = hours[min(int(0.9 * len(hours)), len(hours) - 1)]
    return lo, hi


def busiest_weekday(min_samples: int = 8) -> str | None:
    """The weekday name with the most recorded activity, or None below min_samples."""
    timestamps = _activity_timestamps()
    if len(timestamps) < min_samples:
        return None
    counts = [0] * 7
    for ts in timestamps:
        counts[time.localtime(ts).tm_wday] += 1
    return _WEEKDAYS[counts.index(max(counts))]


def _fmt_hour(hour: int) -> str:
    suffix = "am" if hour < 12 else "pm"
    twelve = hour % 12 or 12
    return f"{twelve}{suffix}"


def behavior_summary(min_samples: int = 8) -> str:
    """One-line habit summary for the system prompt. Empty until enough data."""
    window = work_hours(min_samples)
    if window is None:
        return ""
    parts = [f"usually active {_fmt_hour(window[0])}–{_fmt_hour(window[1])}"]
    weekday = busiest_weekday(min_samples)
    if weekday:
        parts.append(f"most active on {weekday}s")
    return "User habits: " + ", ".join(parts) + "."
