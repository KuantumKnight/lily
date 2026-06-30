"""Decision memory: capture choices together with their reasons."""

import sqlite3
import time
from datetime import datetime

from . import timeline
from .config import DB_PATH


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS decisions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            ts         REAL NOT NULL,
            decision   TEXT NOT NULL,
            reason     TEXT NOT NULL,
            context    TEXT NOT NULL DEFAULT ''
        )
        """
    )
    return conn


def remember(decision: str, reason: str, context: str = "") -> int:
    decision = decision.strip()
    reason = reason.strip()
    context = context.strip()
    if not decision or not reason:
        raise ValueError("decision and reason are required")
    conn = _conn()
    with conn:
        cur = conn.execute(
            "INSERT INTO decisions (ts, decision, reason, context) VALUES (?, ?, ?, ?)",
            (time.time(), decision, reason, context),
        )
    conn.close()
    event_id = int(cur.lastrowid)
    timeline.append_event(
        "decision",
        decision,
        f"Reason: {reason}" + (f"\nContext: {context}" if context else ""),
        {"decision_id": event_id},
    )
    return event_id


def recent(limit: int = 20) -> list[dict]:
    limit = max(1, min(int(limit), 100))
    conn = _conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, ts, decision, reason, context FROM decisions ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def search(query: str, limit: int = 20) -> list[dict]:
    query = query.strip()
    if not query:
        return recent(limit)
    limit = max(1, min(int(limit), 100))
    conn = _conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT id, ts, decision, reason, context
        FROM decisions
        WHERE decision LIKE ? OR reason LIKE ? OR context LIKE ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (f"%{query}%", f"%{query}%", f"%{query}%", limit),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def format_rows(rows: list[dict]) -> str:
    if not rows:
        return "No decision memories found."
    lines = []
    for row in rows:
        when = datetime.fromtimestamp(row["ts"]).strftime("%Y-%m-%d %H:%M")
        line = f"{when} #{row['id']}: {row['decision']}\n  why: {row['reason']}"
        if row.get("context"):
            line += f"\n  context: {row['context']}"
        lines.append(line)
    return "\n".join(lines)
