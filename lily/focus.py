"""Anti-distraction focus blocks."""

import sqlite3
import time
from datetime import datetime

from .config import DB_PATH

STATE_KEY = "focus_until"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS state (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    return conn


def start(minutes: int = 25, reason: str = "focus") -> str:
    minutes = max(5, min(int(minutes), 240))
    until = time.time() + minutes * 60
    conn = _conn()
    with conn:
        conn.execute(
            "INSERT INTO state (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (STATE_KEY, str(until)),
        )
        conn.execute(
            "INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)",
            ("focus_reason", reason.strip() or "focus"),
        )
    conn.close()
    return f"Focus protected until {_fmt(until)} ({minutes} min): {reason.strip() or 'focus'}"


def end() -> str:
    conn = _conn()
    with conn:
        conn.execute("DELETE FROM state WHERE key IN (?, ?)", (STATE_KEY, "focus_reason"))
    conn.close()
    return "Focus block ended."


def active() -> bool:
    until = _until()
    return bool(until and until > time.time())


def status() -> str:
    until = _until()
    if not until or until <= time.time():
        return "No active focus block."
    return f"Focus protected until {_fmt(until)}."


def negotiate(request: str, minutes: int = 25) -> str:
    """Suggest a focus block in response to a distraction request."""
    if active():
        return status() + " I can batch this unless it is urgent."
    return start(minutes=minutes, reason=request or "protect focus")


def _until() -> float | None:
    conn = _conn()
    row = conn.execute("SELECT value FROM state WHERE key = ?", (STATE_KEY,)).fetchone()
    conn.close()
    if not row:
        return None
    try:
        return float(row[0])
    except (TypeError, ValueError):
        return None


def _fmt(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%H:%M")
