"""Runtime schedulers for local Lily jobs."""

import sqlite3
import time
from collections.abc import Callable

from .config import DB_PATH
from .log import get_logger

log = get_logger("scheduler")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
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


def _ensure_column(conn: sqlite3.Connection, table: str, name: str, column_type: str) -> None:
    cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if name not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {column_type}")


def poll_due_reminders(on_reminder: Callable[[sqlite3.Row], None]) -> int:
    """Fire due reminders once. Returns the number fired."""
    now = time.time()
    conn = _conn()
    rows = conn.execute(
        """
        SELECT id, due_at, content
        FROM reminders
        WHERE completed_ts IS NULL
          AND fired_ts IS NULL
          AND due_ts IS NOT NULL
          AND due_ts <= ?
        ORDER BY due_ts, id
        """,
        (now,),
    ).fetchall()

    fired = 0
    with conn:
        for row in rows:
            cur = conn.execute(
                """
                UPDATE reminders
                SET fired_ts = ?
                WHERE id = ? AND fired_ts IS NULL AND completed_ts IS NULL
                """,
                (now, row["id"]),
            )
            if cur.rowcount:
                on_reminder(row)
                fired += 1
    conn.close()
    return fired


def start_reminder_scheduler(on_reminder: Callable[[sqlite3.Row], None]):
    """Start the APScheduler-backed reminder poller. Returns the scheduler or None."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        log.warning("APScheduler is not installed; reminders will not fire")
        return None

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        poll_due_reminders,
        "interval",
        seconds=5,
        args=[on_reminder],
        id="reminder-poller",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    log.info("reminder scheduler started")
    return scheduler
