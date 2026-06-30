"""Per-agent access audit log."""

import sqlite3
import time
from datetime import datetime

from .config import DB_PATH


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_audit (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            ts       REAL NOT NULL,
            agent    TEXT NOT NULL,
            action   TEXT NOT NULL,
            resource TEXT NOT NULL,
            detail   TEXT NOT NULL DEFAULT ''
        )
        """
    )
    return conn


def record(agent: str, action: str, resource: str, detail: str = "") -> int:
    conn = _conn()
    with conn:
        cur = conn.execute(
            """
            INSERT INTO agent_audit (ts, agent, action, resource, detail)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                time.time(),
                agent.strip() or "unknown",
                action.strip() or "access",
                resource.strip() or "unknown",
                detail.strip(),
            ),
        )
    conn.close()
    return int(cur.lastrowid)


def recent(limit: int = 50, agent: str = "") -> list[dict]:
    limit = max(1, min(int(limit), 200))
    conn = _conn()
    conn.row_factory = sqlite3.Row
    if agent.strip():
        rows = conn.execute(
            """
            SELECT id, ts, agent, action, resource, detail
            FROM agent_audit
            WHERE agent = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (agent.strip(), limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT id, ts, agent, action, resource, detail
            FROM agent_audit
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def format_rows(rows: list[dict]) -> str:
    if not rows:
        return "No audit entries found."
    lines = []
    for row in rows:
        when = datetime.fromtimestamp(row["ts"]).strftime("%Y-%m-%d %H:%M:%S")
        detail = f" — {row['detail']}" if row.get("detail") else ""
        lines.append(
            f"{when} #{row['id']} {row['agent']} {row['action']} {row['resource']}{detail}"
        )
    return "\n".join(lines)
