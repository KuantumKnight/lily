"""SQLite-backed notes and reminders."""

import re
import sqlite3
import time
from datetime import datetime, timedelta

from ..config import DB_PATH
from . import tool


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            created_ts REAL NOT NULL,
            content    TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reminders (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            created_ts   REAL NOT NULL,
            due_at       TEXT,
            due_ts       REAL,
            content      TEXT NOT NULL,
            fired_ts     REAL,
            completed_ts REAL
        )
        """
    )
    _ensure_column(conn, "reminders", "due_ts", "REAL")
    _ensure_column(conn, "reminders", "fired_ts", "REAL")
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, name: str, column_type: str) -> None:
    cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if name not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {column_type}")


def _parse_due_ts(due_at: str | None) -> float | None:
    if not due_at:
        return None

    text = due_at.strip()
    if not text:
        return None

    for parser in (_parse_relative_due, _parse_absolute_due):
        parsed = parser(text)
        if parsed is not None:
            return parsed.timestamp()
    return None


def _parse_absolute_due(text: str) -> datetime | None:
    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %I:%M %p", "%Y-%m-%d %I %p"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _parse_relative_due(text: str) -> datetime | None:
    match = re.fullmatch(
        r"in\s+(\d+)\s+(second|seconds|minute|minutes|hour|hours|day|days)",
        text.lower(),
    )
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2).rstrip("s")
    return datetime.now() + timedelta(**{unit + "s": amount})


def _format_rows(rows: list[sqlite3.Row], *, include_due: bool = False) -> str:
    if not rows:
        return "None found."

    lines: list[str] = []
    for row in rows:
        prefix = f"#{row['id']}"
        if include_due:
            due = row["due_at"] or "no due time"
            prefix = f"{prefix} [{due}]"
        lines.append(f"{prefix}: {row['content']}")
    return "\n".join(lines)


@tool(
    description="Save a short note locally. Use when the user asks Lily to remember, note, or write something down."
)
def add_note(content: str) -> str:
    content = content.strip()
    if not content:
        return "[error] note content is empty"

    conn = _conn()
    with conn:
        cur = conn.execute(
            "INSERT INTO notes (created_ts, content) VALUES (?, ?)",
            (time.time(), content),
        )
    conn.close()
    return f"Saved note #{cur.lastrowid}."


@tool(description="List recent saved notes from Lily's local notebook.")
def list_notes(limit: int = 10) -> str:
    limit = max(1, min(int(limit), 50))
    conn = _conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, content FROM notes ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return _format_rows(rows)


@tool(
    description="Save a local reminder. due_at is optional local time, preferably 'YYYY-MM-DD HH:MM' or relative text like 'in 10 minutes'."
)
def add_reminder(content: str, due_at: str = "") -> str:
    content = content.strip()
    due_at = due_at.strip() or None
    due_ts = _parse_due_ts(due_at)
    if not content:
        return "[error] reminder content is empty"

    conn = _conn()
    with conn:
        cur = conn.execute(
            """
            INSERT INTO reminders (created_ts, due_at, due_ts, content)
            VALUES (?, ?, ?, ?)
            """,
            (time.time(), due_at, due_ts, content),
        )
    conn.close()

    suffix = f" for {due_at}" if due_at else ""
    if due_at and due_ts is None:
        suffix += " (unscheduled: Lily could not parse that time)"
    return f"Saved reminder #{cur.lastrowid}{suffix}."


@tool(description="List pending reminders saved locally.")
def list_reminders(limit: int = 10) -> str:
    limit = max(1, min(int(limit), 50))
    conn = _conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT id, due_at, content
        FROM reminders
        WHERE completed_ts IS NULL
        ORDER BY due_ts IS NULL, due_ts, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return _format_rows(rows, include_due=True)


@tool(description="Mark a local reminder as completed by its numeric reminder_id.")
def complete_reminder(reminder_id: int) -> str:
    conn = _conn()
    with conn:
        cur = conn.execute(
            """
            UPDATE reminders
            SET completed_ts = ?
            WHERE id = ? AND completed_ts IS NULL
            """,
            (time.time(), int(reminder_id)),
        )
    conn.close()

    if cur.rowcount == 0:
        return f"No pending reminder #{reminder_id} found."
    return f"Completed reminder #{reminder_id}."
