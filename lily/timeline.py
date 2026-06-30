"""Append-only chronological timeline for Lily Prime."""

import json
import sqlite3
import time
from datetime import datetime

from .config import DB_PATH


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS timeline_events (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts        REAL NOT NULL,
            kind      TEXT NOT NULL,
            title     TEXT NOT NULL,
            content   TEXT NOT NULL,
            metadata  TEXT NOT NULL DEFAULT '{}'
        )
        """
    )
    return conn


def append_event(
    kind: str,
    title: str,
    content: str,
    metadata: dict | None = None,
    ts: float | None = None,
) -> int:
    """Append one event and return its id. Existing events are never mutated."""
    kind = kind.strip() or "event"
    title = title.strip() or kind
    content = content.strip()
    payload = json.dumps(metadata or {}, sort_keys=True)
    conn = _conn()
    with conn:
        cur = conn.execute(
            """
            INSERT INTO timeline_events (ts, kind, title, content, metadata)
            VALUES (?, ?, ?, ?, ?)
            """,
            (time.time() if ts is None else ts, kind, title, content, payload),
        )
    conn.close()
    return int(cur.lastrowid)


def recent(limit: int = 20) -> list[dict]:
    """Return recent events newest-first."""
    limit = max(1, min(int(limit), 100))
    conn = _conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT id, ts, kind, title, content, metadata
        FROM timeline_events
        ORDER BY ts DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [_row_dict(row) for row in rows]


def between(start_ts: float, end_ts: float, limit: int = 100) -> list[dict]:
    """Return events in chronological order for a time window."""
    limit = max(1, min(int(limit), 500))
    conn = _conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT id, ts, kind, title, content, metadata
        FROM timeline_events
        WHERE ts >= ? AND ts < ?
        ORDER BY ts ASC, id ASC
        LIMIT ?
        """,
        (start_ts, end_ts, limit),
    ).fetchall()
    conn.close()
    return [_row_dict(row) for row in rows]


def search(query: str, limit: int = 20) -> list[dict]:
    """Keyword search timeline titles/content newest-first."""
    query = query.strip()
    if not query:
        return recent(limit)
    limit = max(1, min(int(limit), 100))
    conn = _conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT id, ts, kind, title, content, metadata
        FROM timeline_events
        WHERE title LIKE ? OR content LIKE ? OR kind LIKE ?
        ORDER BY ts DESC, id DESC
        LIMIT ?
        """,
        (f"%{query}%", f"%{query}%", f"%{query}%", limit),
    ).fetchall()
    conn.close()
    return [_row_dict(row) for row in rows]


def format_events(events: list[dict]) -> str:
    if not events:
        return "No timeline events found."
    lines = []
    for event in events:
        when = datetime.fromtimestamp(event["ts"]).strftime("%Y-%m-%d %H:%M")
        lines.append(f"{when} [{event['kind']}] {event['title']}: {event['content']}")
    return "\n".join(lines)


def _row_dict(row: sqlite3.Row) -> dict:
    item = dict(row)
    try:
        item["metadata"] = json.loads(item.get("metadata") or "{}")
    except json.JSONDecodeError:
        item["metadata"] = {}
    return item
