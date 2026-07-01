"""Feedback memory: turn ratings into preference signals."""

import re
import sqlite3
import time

from .config import DB_PATH

_STOP = {
    "the", "and", "for", "that", "this", "with", "from", "into", "your", "you",
    "was", "were", "are", "but", "not", "too", "very", "more", "less",
}


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback_events (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            ts       REAL NOT NULL,
            rating   INTEGER NOT NULL,
            target   TEXT NOT NULL,
            reason   TEXT NOT NULL,
            context  TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS preference_signals (
            key       TEXT PRIMARY KEY,
            weight    REAL NOT NULL,
            evidence  INTEGER NOT NULL,
            updated_ts REAL NOT NULL
        )
        """
    )
    return conn


def record(rating: str, target: str, reason: str = "", context: str = "") -> int:
    value = _rating_value(rating)
    target = target.strip()
    reason = reason.strip()
    context = context.strip()
    conn = _conn()
    with conn:
        cur = conn.execute(
            """
            INSERT INTO feedback_events (ts, rating, target, reason, context)
            VALUES (?, ?, ?, ?, ?)
            """,
            (time.time(), value, target, reason, context),
        )
        for key in _signals(target + " " + reason + " " + context):
            conn.execute(
                """
                INSERT INTO preference_signals (key, weight, evidence, updated_ts)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(key) DO UPDATE SET
                    weight = preference_signals.weight + excluded.weight,
                    evidence = preference_signals.evidence + 1,
                    updated_ts = excluded.updated_ts
                """,
                (key, float(value), time.time()),
            )
    conn.close()
    return int(cur.lastrowid)


def preferences(limit: int = 20) -> list[dict]:
    limit = max(1, min(int(limit), 100))
    conn = _conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT key, weight, evidence, updated_ts
        FROM preference_signals
        ORDER BY ABS(weight) DESC, evidence DESC, key ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def summary(limit: int = 12) -> str:
    rows = preferences(limit)
    if not rows:
        return "No feedback preferences learned yet."
    lines = []
    for row in rows:
        direction = "prefers" if row["weight"] > 0 else "avoids"
        confidence = min(1.0, abs(row["weight"]) / max(row["evidence"], 1))
        lines.append(f"{direction} {row['key']} ({row['evidence']} signals, {confidence:.0%})")
    return "Learned preference signals:\n" + "\n".join(lines)


def _rating_value(rating: str) -> int:
    lowered = str(rating).strip().lower()
    if lowered in {"up", "good", "positive", "like", "+", "+1", "thumbs up"}:
        return 1
    if lowered in {"down", "bad", "negative", "dislike", "-", "-1", "thumbs down"}:
        return -1
    raise ValueError("rating must be up/down or positive/negative")


def _signals(text: str) -> list[str]:
    words = [
        word for word in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
        if word not in _STOP
    ]
    return sorted(set(words))[:20]
