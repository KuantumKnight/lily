"""Lily's local dashboard — a small FastAPI app serving her state as JSON (E20).

Bound to localhost only; this is a personal, local-first view, never exposed. The
*data provider* functions (``system_card``, ``habits_card``, …) are plain dicts with no
web dependency, so they're fully testable headless and reused by the API layer. FastAPI
and uvicorn are imported lazily inside :func:`create_app` / :func:`start_in_thread`, so
Lily runs fine when they aren't installed — the dashboard just stays off.

E21 adds the static UI + card providers; E22 adds a websocket bridging the bus. This
file is the single app extended across all three.
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

import psutil

from . import adaptive_dashboard, agents, brain, brief, bus, chat, goals, memory, timeline
from . import mode as mode_module
from . import tools
from .agents import planner as planner_agent
from .config import DASHBOARD_ADAPTIVE, DASHBOARD_HOST, DASHBOARD_PORT
from .log import get_logger

log = get_logger("dashboard")

STATIC_DIR = Path(__file__).resolve().parent / "dashboard_static"


class DashboardUnavailable(RuntimeError):
    """Raised when FastAPI/uvicorn aren't installed."""


def _gb(n: int) -> float:
    return round(n / (1024**3), 1)


# ---- data providers (no web dependency) ---------------------------------------

def system_card() -> dict:
    vm = psutil.virtual_memory()
    drive = os.environ.get("SystemDrive", "C:") + os.sep
    disk = psutil.disk_usage(drive)
    card = {
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "cpu_threads": psutil.cpu_count(logical=True),
        "ram_used_gb": _gb(vm.used),
        "ram_total_gb": _gb(vm.total),
        "ram_percent": vm.percent,
        "disk_used_gb": _gb(disk.used),
        "disk_total_gb": _gb(disk.total),
        "disk_percent": disk.percent,
    }
    try:
        battery = psutil.sensors_battery()
    except (AttributeError, OSError):
        battery = None
    if battery is not None:
        card["battery_percent"] = round(battery.percent)
        card["battery_charging"] = bool(battery.power_plugged)
    return card


def status_card() -> dict:
    return {
        "mode": mode_module.current(),
        "agents": len(agents.all_agents()),
        "tools": len(tools.schemas() or []),
    }


def profile_card() -> dict:
    """Return the operating profile Lily should present in the dashboard.

    Profiles are the product language above the existing passive/active resource
    switch. Until richer profile automation exists, the current mode is the
    source of truth and the extra profiles are surfaced as available intents.
    """
    current = mode_module.current()
    profiles = [
        {
            "name": "Passive",
            "key": "passive",
            "summary": "Wake word and watchdogs only.",
            "enabled": ["Wake", "Security"],
        },
        {
            "name": "Active",
            "key": "active",
            "summary": "Reasoning, memory, agents, and automation available.",
            "enabled": ["Voice", "Memory", "Agents", "Dashboard"],
        },
        {
            "name": "Deep Work",
            "key": "deep_work",
            "summary": "Distractions batched while goal work stays visible.",
            "enabled": ["Focus", "Timeline", "Notifications"],
        },
        {
            "name": "Coding",
            "key": "coding",
            "summary": "Repository, terminal, git, and error context first.",
            "enabled": ["Git", "Dev", "Timeline"],
        },
        {
            "name": "Research",
            "key": "research",
            "summary": "Reading, PDF analysis, and knowledge capture.",
            "enabled": ["Research", "Memory", "Recall"],
        },
    ]
    return {"current": current, "profiles": profiles}


def goal_card() -> dict:
    """Return the active persisted goal plus a compact goal queue."""
    active = goals.active_goal()
    all_goals = goals.list_goals(limit=8)
    queue = [
        {
            "id": item["id"],
            "title": item["title"],
            "status": item["status"],
            "progress": item["progress"],
            "priority": item["priority"],
        }
        for item in all_goals
        if not active or item["id"] != active["id"]
    ]

    if active:
        recent = goals.recent_events(active["id"], limit=1)
        last_worked = (
            datetime.fromtimestamp(recent[0]["ts"]).strftime("%Y-%m-%d %H:%M")
            if recent else ""
        )
        return {
            "id": active["id"],
            "goal": active["title"],
            "outcome": active["outcome"],
            "success_criteria": active["success_criteria"],
            "status": active["status"],
            "priority": active["priority"],
            "due_at": active["due_at"],
            "progress": active["progress"],
            "blocker": active["blocker"],
            "next_action": active["next_action"],
            "last_worked": last_worked,
            "tasks": active["tasks"],
            "task_summary": active["task_summary"],
            "queue": queue,
            "suggestions": [
                f"Continue {active['title']}",
                f"Plan the next steps for {active['title']}",
                "Open daily brief",
            ],
        }

    # Preserve installations that used state keys before goals were first-class.
    legacy_goal = memory.get_state("active_goal", "") or memory.active_project()
    return {
        "id": None,
        "goal": legacy_goal,
        "status": "legacy" if legacy_goal else "empty",
        "progress": memory.get_state("active_goal_progress", ""),
        "blocker": memory.get_state("active_goal_blocker", ""),
        "next_action": "",
        "last_worked": memory.get_state("active_goal_last_worked", ""),
        "tasks": [],
        "task_summary": {"total": 0, "done": 0, "blocked": 0, "remaining": 0},
        "queue": queue,
        "suggestions": ["Open daily brief", "Ask what next"],
    }


def habits_card() -> dict:
    window = memory.work_hours()
    return {
        "work_hours": list(window) if window else None,
        "busiest_weekday": memory.busiest_weekday(),
        "summary": memory.behavior_summary(),
    }


def memory_facts_card(limit: int = 20) -> dict:
    return {"facts": memory.list_facts(limit)}


def memory_projects_card() -> dict:
    return {"active": memory.active_project(), "projects": memory.list_projects()}


def brief_card() -> dict:
    return {"brief": brief.daily_brief()}


def timeline_card(limit: int = 6) -> dict:
    events = []
    for event in timeline.recent(limit):
        events.append(
            {
                "id": event["id"],
                "ts": event["ts"],
                "time": datetime.fromtimestamp(event["ts"]).strftime("%H:%M"),
                "kind": event["kind"],
                "title": event["title"],
                "content": event["content"],
            }
        )
    return {"events": events}


def agents_card() -> dict:
    roster = [
        {"name": agent.name, "description": agent.description}
        for agent in agents.all_agents()
    ]
    return {"agents": roster}


# ---- live websocket bridge (E22) ----------------------------------------------

# Bus topics worth pushing to the browser. Each nudges the client to refresh its cards.
_LIVE_TOPICS = {
    "mode.changed", "lily.reply", "reminder.fired", "notification.surfaced",
    "notification.queued", "work.digest", "dev.tests", "plan.created",
    "calendar.upcoming", "opportunities.found", "interrupt.raised",
    "goal.created", "goal.updated", "goal.task_added", "goal.task_updated",
    "goal.planned",
}


def _jsonable(payload) -> object:
    """Best-effort make a bus payload JSON-serializable (datetimes etc. -> str)."""
    try:
        return json.loads(json.dumps(payload, default=str))
    except (TypeError, ValueError):
        return None


class _Hub:
    """Tracks connected websockets and fans bus events out to them, thread-safely."""

    def __init__(self):
        self._clients: set = set()
        self._loop = None

    async def connect(self, ws) -> None:
        await ws.accept()
        self._clients.add(ws)
        self._loop = asyncio.get_running_loop()

    def disconnect(self, ws) -> None:
        self._clients.discard(ws)

    async def _send_all(self, msg: dict) -> None:
        for ws in list(self._clients):
            try:
                await ws.send_json(msg)
            except Exception:
                self.disconnect(ws)

    def broadcast(self, msg: dict) -> None:
        """Schedule a fan-out from any thread (no-op until a client + loop exist)."""
        if self._loop is not None and self._clients:
            asyncio.run_coroutine_threadsafe(self._send_all(msg), self._loop)


_hub = _Hub()
_bus_bridged = False


def _on_bus_event(topic: str, payload: object) -> None:
    if topic in _LIVE_TOPICS:
        _hub.broadcast({"event": topic, "payload": _jsonable(payload)})


def all_cards() -> dict:
    """Every card the UI renders, in one payload (used by /api/cards and the websocket)."""
    cards = {
        "status": status_card(),
        "profile": profile_card(),
        "goal": goal_card(),
        "system": system_card(),
        "timeline": timeline_card(),
        "agents": agents_card(),
        "habits": habits_card(),
        "facts": memory_facts_card(10),
        "projects": memory_projects_card(),
    }
    return adaptive_dashboard.select(cards) if DASHBOARD_ADAPTIVE else cards


# ---- app ----------------------------------------------------------------------

def create_app():
    """Build the FastAPI app. Raises DashboardUnavailable if FastAPI isn't installed."""
    try:
        from fastapi import FastAPI, HTTPException, WebSocket
    except ImportError as exc:
        raise DashboardUnavailable(
            "FastAPI is not installed — run: pip install fastapi uvicorn"
        ) from exc

    chat.prepare()
    app = FastAPI(title="Lily", docs_url=None, redoc_url=None)

    @app.get("/api/status")
    def _status():
        return status_card()

    @app.get("/api/status/system")
    def _system():
        return system_card()

    @app.get("/api/habits")
    def _habits():
        return habits_card()

    @app.get("/api/memory/facts")
    def _facts(limit: int = 20):
        return memory_facts_card(limit)

    @app.get("/api/memory/projects")
    def _projects():
        return memory_projects_card()

    @app.get("/api/brief")
    def _brief():
        return brief_card()

    def _goal_failure(exc: Exception):
        status_code = 404 if isinstance(exc, KeyError) else 422
        detail = exc.args[0] if exc.args else str(exc)
        raise HTTPException(status_code=status_code, detail=str(detail)) from exc

    @app.get("/api/goals")
    def _goals(status: str = "", limit: int = 20):
        try:
            return {"goals": goals.list_goals(status=status, limit=limit)}
        except (KeyError, TypeError, ValueError) as exc:
            _goal_failure(exc)

    @app.post("/api/goals")
    def _create_goal(payload: dict):
        try:
            return goals.create_goal(
                title=payload.get("title", ""),
                outcome=payload.get("outcome", ""),
                success_criteria=payload.get("success_criteria", ""),
                priority=payload.get("priority", 3),
                due_at=payload.get("due_at", ""),
                next_action=payload.get("next_action", ""),
                activate=bool(payload.get("activate", True)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            _goal_failure(exc)

    @app.get("/api/goals/{goal_id}")
    def _goal(goal_id: int):
        try:
            return goals.get_goal(goal_id)
        except (KeyError, TypeError, ValueError) as exc:
            _goal_failure(exc)

    @app.patch("/api/goals/{goal_id}")
    def _update_goal(goal_id: int, payload: dict):
        try:
            return goals.update_goal(goal_id, **payload)
        except (KeyError, TypeError, ValueError) as exc:
            _goal_failure(exc)

    @app.post("/api/goals/{goal_id}/activate")
    def _activate_goal(goal_id: int):
        try:
            return goals.set_active(goal_id)
        except (KeyError, TypeError, ValueError) as exc:
            _goal_failure(exc)

    @app.post("/api/goals/{goal_id}/tasks")
    def _create_goal_task(goal_id: int, payload: dict):
        try:
            return goals.add_task(
                goal_id,
                title=payload.get("title", ""),
                assignee=payload.get("assignee", ""),
            )
        except (KeyError, TypeError, ValueError) as exc:
            _goal_failure(exc)

    @app.post("/api/goals/{goal_id}/plan")
    def _plan_goal(goal_id: int):
        try:
            goal = goals.get_goal(goal_id)
            context = [f"Goal: {goal['title']}"]
            if goal["outcome"]:
                context.append(f"Desired outcome: {goal['outcome']}")
            if goal["success_criteria"]:
                context.append(f"Success criteria: {goal['success_criteria']}")
            context.append(
                "Create concrete execution tasks. Do not repeat work already implied "
                "by the goal wording."
            )
            steps = planner_agent.plan("\n".join(context))
            return goals.add_generated_tasks(goal_id, steps)
        except brain.BrainOffline as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except (KeyError, TypeError, ValueError) as exc:
            _goal_failure(exc)

    @app.patch("/api/goals/{goal_id}/tasks/{task_id}")
    def _update_goal_task(goal_id: int, task_id: int, payload: dict):
        try:
            return goals.update_task(goal_id, task_id, **payload)
        except (KeyError, TypeError, ValueError) as exc:
            _goal_failure(exc)

    @app.get("/api/goals/{goal_id}/events")
    def _goal_events(goal_id: int, limit: int = 20):
        try:
            return {"events": goals.recent_events(goal_id, limit=limit)}
        except (KeyError, TypeError, ValueError) as exc:
            _goal_failure(exc)

    @app.get("/api/cards")
    def _cards():
        return all_cards()

    @app.get("/api/chat/history")
    def _chat_history(limit: int = 40):
        return {"messages": memory.recent(max(1, min(limit, 100)))}

    @app.post("/api/chat")
    def _chat(payload: dict):
        message = str(payload.get("message") or "").strip()
        if not message:
            raise HTTPException(status_code=422, detail="Message cannot be empty.")
        if len(message) > 8000:
            raise HTTPException(status_code=422, detail="Message is too long (8,000 character limit).")
        try:
            reply = chat.respond(message)
        except brain.BrainOffline as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return {"reply": reply}

    @app.websocket("/ws")
    async def _ws(websocket: WebSocket):
        await _hub.connect(websocket)
        try:
            await websocket.send_json({"event": "snapshot", "cards": all_cards()})
            while True:
                await websocket.receive_text()  # client pings; we just keep the socket open
        except Exception:
            pass
        finally:
            _hub.disconnect(websocket)

    # Bridge the bus into the hub once (events -> connected browsers).
    global _bus_bridged
    if not _bus_bridged:
        bus.subscribe("*", _on_bus_event)
        _bus_bridged = True

    # Static UI (E21) — served at the root. html=True makes "/" serve index.html.
    if STATIC_DIR.is_dir():
        from fastapi.staticfiles import StaticFiles

        app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app


def start_in_thread(host: str | None = None, port: int | None = None):
    """Launch uvicorn in a daemon thread bound to localhost. Returns the thread."""
    import threading

    try:
        import uvicorn
    except ImportError as exc:
        raise DashboardUnavailable(
            "uvicorn is not installed — run: pip install fastapi uvicorn"
        ) from exc

    app = create_app()
    host = host or DASHBOARD_HOST
    port = port or DASHBOARD_PORT
    # wsproto is a stable sans-io websocket impl; avoids version skew with the
    # 'websockets' package on the server side. Falls back to auto if unavailable.
    ws_impl = "wsproto"
    try:
        import wsproto  # noqa: F401
    except ImportError:
        ws_impl = "auto"
    config = uvicorn.Config(app, host=host, port=port, log_level="warning", ws=ws_impl)
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, name="lily-dashboard", daemon=True)
    thread.start()
    log.info("dashboard serving on http://%s:%d", host, port)
    return thread
