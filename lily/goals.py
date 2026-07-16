"""Persisted goals, tasks, and goal activity for SentinelOS."""

from __future__ import annotations

import json
import sqlite3
import time

from . import bus, timeline
from .config import DB_PATH

GOAL_STATUSES = {"planned", "active", "paused", "blocked", "completed", "cancelled"}
TASK_STATUSES = {"todo", "doing", "blocked", "done"}


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS goals (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            created_ts       REAL NOT NULL,
            updated_ts       REAL NOT NULL,
            title            TEXT NOT NULL,
            outcome          TEXT NOT NULL DEFAULT '',
            success_criteria TEXT NOT NULL DEFAULT '',
            status           TEXT NOT NULL DEFAULT 'planned',
            priority         INTEGER NOT NULL DEFAULT 3,
            due_at           TEXT NOT NULL DEFAULT '',
            manual_progress  INTEGER NOT NULL DEFAULT 0,
            blocker          TEXT NOT NULL DEFAULT '',
            next_action      TEXT NOT NULL DEFAULT '',
            active           INTEGER NOT NULL DEFAULT 0,
            completed_ts     REAL
        );

        CREATE TABLE IF NOT EXISTS goal_tasks (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id      INTEGER NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
            created_ts   REAL NOT NULL,
            updated_ts   REAL NOT NULL,
            title        TEXT NOT NULL,
            status       TEXT NOT NULL DEFAULT 'todo',
            position     INTEGER NOT NULL DEFAULT 0,
            assignee     TEXT NOT NULL DEFAULT '',
            completed_ts REAL
        );

        CREATE TABLE IF NOT EXISTS goal_events (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id  INTEGER NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
            ts       REAL NOT NULL,
            kind     TEXT NOT NULL,
            detail   TEXT NOT NULL,
            metadata TEXT NOT NULL DEFAULT '{}'
        );

        CREATE INDEX IF NOT EXISTS idx_goals_active ON goals(active, updated_ts DESC);
        CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status, priority, updated_ts DESC);
        CREATE INDEX IF NOT EXISTS idx_goal_tasks_goal ON goal_tasks(goal_id, position, id);
        CREATE INDEX IF NOT EXISTS idx_goal_events_goal ON goal_events(goal_id, ts DESC);
        """
    )


def _clean_required(value: str, field: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise ValueError(f"{field} is required")
    return cleaned


def _priority(value: int) -> int:
    return max(1, min(5, int(value)))


def _goal_dict(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    tasks = conn.execute(
        """
        SELECT id, goal_id, title, status, position, assignee, created_ts, updated_ts,
               completed_ts
        FROM goal_tasks
        WHERE goal_id = ?
        ORDER BY position, id
        """,
        (row["id"],),
    ).fetchall()
    task_items = [dict(task) for task in tasks]
    done = sum(task["status"] == "done" for task in tasks)
    blocked = sum(task["status"] == "blocked" for task in tasks)
    progress = round(done / len(tasks) * 100) if tasks else int(row["manual_progress"])
    item = dict(row)
    item["active"] = bool(item["active"])
    item["progress"] = progress
    item["tasks"] = task_items
    item["task_summary"] = {
        "total": len(tasks),
        "done": done,
        "blocked": blocked,
        "remaining": len(tasks) - done,
    }
    return item


def _get(conn: sqlite3.Connection, goal_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM goals WHERE id = ?", (int(goal_id),)).fetchone()
    if row is None:
        raise KeyError(f"goal {goal_id} was not found")
    return row


def _record(goal_id: int, kind: str, detail: str, metadata: dict | None = None) -> None:
    now = time.time()
    payload = metadata or {}
    conn = _conn()
    with conn:
        conn.execute(
            "INSERT INTO goal_events (goal_id, ts, kind, detail, metadata) VALUES (?, ?, ?, ?, ?)",
            (int(goal_id), now, kind, detail, json.dumps(payload, sort_keys=True)),
        )
    conn.close()
    event = {"goal_id": int(goal_id), "kind": kind, "detail": detail, **payload}
    bus.publish(f"goal.{kind}", event)
    timeline.append_event(
        "goal",
        detail,
        payload.get("title", ""),
        {"goal_id": int(goal_id), "goal_event": kind, **payload},
        ts=now,
    )


def create_goal(
    title: str,
    outcome: str = "",
    success_criteria: str = "",
    priority: int = 3,
    due_at: str = "",
    next_action: str = "",
    activate: bool = True,
) -> dict:
    """Create a goal and optionally make it the single active goal."""
    title = _clean_required(title, "title")
    now = time.time()
    conn = _conn()
    with conn:
        if activate:
            conn.execute("UPDATE goals SET active = 0 WHERE active = 1")
        cur = conn.execute(
            """
            INSERT INTO goals (
                created_ts, updated_ts, title, outcome, success_criteria, status,
                priority, due_at, next_action, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now,
                now,
                title,
                str(outcome or "").strip(),
                str(success_criteria or "").strip(),
                "active" if activate else "planned",
                _priority(priority),
                str(due_at or "").strip(),
                str(next_action or "").strip(),
                1 if activate else 0,
            ),
        )
        goal_id = int(cur.lastrowid)
        result = _goal_dict(conn, _get(conn, goal_id))
    conn.close()
    _record(goal_id, "created", f"Goal created: {title}", {"title": title})
    return result


def get_goal(goal_id: int) -> dict:
    conn = _conn()
    result = _goal_dict(conn, _get(conn, goal_id))
    conn.close()
    return result


def active_goal() -> dict | None:
    conn = _conn()
    row = conn.execute(
        "SELECT * FROM goals WHERE active = 1 ORDER BY updated_ts DESC, id DESC LIMIT 1"
    ).fetchone()
    result = _goal_dict(conn, row) if row is not None else None
    conn.close()
    return result


def list_goals(status: str = "", limit: int = 20) -> list[dict]:
    limit = max(1, min(int(limit), 100))
    conn = _conn()
    if status:
        if status not in GOAL_STATUSES:
            conn.close()
            raise ValueError(f"invalid goal status: {status}")
        rows = conn.execute(
            """
            SELECT * FROM goals WHERE status = ?
            ORDER BY active DESC, priority, updated_ts DESC LIMIT ?
            """,
            (status, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM goals
            ORDER BY active DESC,
                     CASE status WHEN 'completed' THEN 1 WHEN 'cancelled' THEN 2 ELSE 0 END,
                     priority, updated_ts DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    results = [_goal_dict(conn, row) for row in rows]
    conn.close()
    return results


def update_goal(goal_id: int, **changes) -> dict:
    """Update editable goal fields and record one goal event."""
    allowed = {
        "title", "outcome", "success_criteria", "status", "priority", "due_at",
        "manual_progress", "blocker", "next_action",
    }
    updates = {key: value for key, value in changes.items() if key in allowed}
    if not updates:
        return get_goal(goal_id)
    if "title" in updates:
        updates["title"] = _clean_required(updates["title"], "title")
    if "status" in updates and updates["status"] not in GOAL_STATUSES:
        raise ValueError(f"invalid goal status: {updates['status']}")
    if "priority" in updates:
        updates["priority"] = _priority(updates["priority"])
    if "manual_progress" in updates:
        updates["manual_progress"] = max(0, min(100, int(updates["manual_progress"])))
    for key in ("outcome", "success_criteria", "due_at", "blocker", "next_action"):
        if key in updates:
            updates[key] = str(updates[key] or "").strip()

    now = time.time()
    conn = _conn()
    with conn:
        current = _get(conn, goal_id)
        if updates.get("status") == "active":
            conn.execute("UPDATE goals SET active = 0 WHERE active = 1 AND id != ?", (goal_id,))
            updates["active"] = 1
        elif updates.get("status") in {"completed", "cancelled"}:
            updates["active"] = 0
            updates["completed_ts"] = now if updates["status"] == "completed" else None
        updates["updated_ts"] = now
        assignments = ", ".join(f"{key} = ?" for key in updates)
        conn.execute(
            f"UPDATE goals SET {assignments} WHERE id = ?",
            (*updates.values(), int(goal_id)),
        )
        result = _goal_dict(conn, _get(conn, goal_id))
    conn.close()
    changed = ", ".join(sorted(key for key in updates if key not in {"updated_ts", "active"}))
    _record(
        goal_id,
        "updated",
        f"Goal updated: {result['title']}",
        {"title": result["title"], "fields": changed, "previous_status": current["status"]},
    )
    return result


def set_active(goal_id: int) -> dict:
    goal = get_goal(goal_id)
    if goal["status"] in {"completed", "cancelled"}:
        raise ValueError("a completed or cancelled goal cannot be activated")
    return update_goal(goal_id, status="active")


def add_task(goal_id: int, title: str, assignee: str = "") -> dict:
    title = _clean_required(title, "task title")
    now = time.time()
    conn = _conn()
    with conn:
        goal = _get(conn, goal_id)
        position = conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 FROM goal_tasks WHERE goal_id = ?",
            (int(goal_id),),
        ).fetchone()[0]
        cur = conn.execute(
            """
            INSERT INTO goal_tasks (
                goal_id, created_ts, updated_ts, title, status, position, assignee
            ) VALUES (?, ?, ?, ?, 'todo', ?, ?)
            """,
            (int(goal_id), now, now, title, int(position), str(assignee or "").strip()),
        )
        task_id = int(cur.lastrowid)
        conn.execute("UPDATE goals SET updated_ts = ? WHERE id = ?", (now, int(goal_id)))
        task = dict(conn.execute("SELECT * FROM goal_tasks WHERE id = ?", (task_id,)).fetchone())
    conn.close()
    _record(
        goal_id,
        "task_added",
        f"Task added: {title}",
        {"title": goal["title"], "task_id": task_id, "task": title},
    )
    return task


def add_generated_tasks(
    goal_id: int,
    titles: list[str],
    assignee: str = "planner",
) -> dict:
    """Append unique generated tasks and return the refreshed goal."""
    cleaned: list[str] = []
    seen: set[str] = set()
    usable_count = 0
    for title in titles:
        item = str(title or "").strip()
        usable_count += bool(item)
        key = item.casefold()
        if item and key not in seen:
            cleaned.append(item)
            seen.add(key)
    if not cleaned:
        raise ValueError("the planner returned no usable tasks")

    now = time.time()
    conn = _conn()
    with conn:
        goal = _get(conn, goal_id)
        existing = {
            row[0].strip().casefold()
            for row in conn.execute(
                "SELECT title FROM goal_tasks WHERE goal_id = ?",
                (int(goal_id),),
            )
        }
        position = conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 FROM goal_tasks WHERE goal_id = ?",
            (int(goal_id),),
        ).fetchone()[0]
        added = []
        for title in cleaned:
            if title.casefold() in existing:
                continue
            cur = conn.execute(
                """
                INSERT INTO goal_tasks (
                    goal_id, created_ts, updated_ts, title, status, position, assignee
                ) VALUES (?, ?, ?, ?, 'todo', ?, ?)
                """,
                (
                    int(goal_id),
                    now,
                    now,
                    title,
                    int(position),
                    str(assignee or "").strip(),
                ),
            )
            added.append(
                {
                    "id": int(cur.lastrowid),
                    "title": title,
                    "position": int(position),
                }
            )
            existing.add(title.casefold())
            position += 1

        if added:
            conn.execute(
                """
                UPDATE goals
                SET updated_ts = ?,
                    next_action = CASE WHEN next_action = '' THEN ? ELSE next_action END
                WHERE id = ?
                """,
                (now, added[0]["title"], int(goal_id)),
            )
        result = _goal_dict(conn, _get(conn, goal_id))
    conn.close()

    if added:
        _record(
            goal_id,
            "planned",
            f"Plan generated: {len(added)} tasks added",
            {
                "title": goal["title"],
                "tasks": [item["title"] for item in added],
                "assignee": str(assignee or "").strip(),
            },
        )
    return {
        "goal": result,
        "added": added,
        "skipped": usable_count - len(added),
    }


def update_task(goal_id: int, task_id: int, **changes) -> dict:
    allowed = {"title", "status", "position", "assignee"}
    updates = {key: value for key, value in changes.items() if key in allowed}
    if not updates:
        return get_task(goal_id, task_id)
    if "title" in updates:
        updates["title"] = _clean_required(updates["title"], "task title")
    if "status" in updates and updates["status"] not in TASK_STATUSES:
        raise ValueError(f"invalid task status: {updates['status']}")
    if "position" in updates:
        updates["position"] = max(0, int(updates["position"]))
    if "assignee" in updates:
        updates["assignee"] = str(updates["assignee"] or "").strip()

    now = time.time()
    conn = _conn()
    with conn:
        goal = _get(conn, goal_id)
        task = conn.execute(
            "SELECT * FROM goal_tasks WHERE id = ? AND goal_id = ?",
            (int(task_id), int(goal_id)),
        ).fetchone()
        if task is None:
            raise KeyError(f"task {task_id} was not found for goal {goal_id}")
        if updates.get("status") == "done":
            updates["completed_ts"] = now
        elif "status" in updates:
            updates["completed_ts"] = None
        updates["updated_ts"] = now
        assignments = ", ".join(f"{key} = ?" for key in updates)
        conn.execute(
            f"UPDATE goal_tasks SET {assignments} WHERE id = ? AND goal_id = ?",
            (*updates.values(), int(task_id), int(goal_id)),
        )
        conn.execute("UPDATE goals SET updated_ts = ? WHERE id = ?", (now, int(goal_id)))
        result = dict(
            conn.execute(
                "SELECT * FROM goal_tasks WHERE id = ? AND goal_id = ?",
                (int(task_id), int(goal_id)),
            ).fetchone()
        )
    conn.close()
    _record(
        goal_id,
        "task_updated",
        f"Task updated: {result['title']}",
        {"title": goal["title"], "task_id": int(task_id), "task_status": result["status"]},
    )
    return result


def get_task(goal_id: int, task_id: int) -> dict:
    conn = _conn()
    row = conn.execute(
        "SELECT * FROM goal_tasks WHERE id = ? AND goal_id = ?",
        (int(task_id), int(goal_id)),
    ).fetchone()
    conn.close()
    if row is None:
        raise KeyError(f"task {task_id} was not found for goal {goal_id}")
    return dict(row)


def recent_events(goal_id: int, limit: int = 20) -> list[dict]:
    limit = max(1, min(int(limit), 100))
    conn = _conn()
    _get(conn, goal_id)
    rows = conn.execute(
        """
        SELECT id, goal_id, ts, kind, detail, metadata
        FROM goal_events WHERE goal_id = ? ORDER BY ts DESC, id DESC LIMIT ?
        """,
        (int(goal_id), limit),
    ).fetchall()
    conn.close()
    events = []
    for row in rows:
        item = dict(row)
        try:
            item["metadata"] = json.loads(item["metadata"] or "{}")
        except json.JSONDecodeError:
            item["metadata"] = {}
        events.append(item)
    return events
