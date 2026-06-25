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
from pathlib import Path

import psutil

from . import agents, brief, bus, memory
from . import mode as mode_module
from . import tools
from .config import DASHBOARD_HOST, DASHBOARD_PORT
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


# ---- live websocket bridge (E22) ----------------------------------------------

# Bus topics worth pushing to the browser. Each nudges the client to refresh its cards.
_LIVE_TOPICS = {
    "mode.changed", "lily.reply", "reminder.fired", "notification.surfaced",
    "notification.queued", "work.digest", "dev.tests", "plan.created",
    "calendar.upcoming", "opportunities.found", "interrupt.raised",
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
    return {
        "status": status_card(),
        "system": system_card(),
        "habits": habits_card(),
        "facts": memory_facts_card(10),
        "projects": memory_projects_card(),
    }


# ---- app ----------------------------------------------------------------------

def create_app():
    """Build the FastAPI app. Raises DashboardUnavailable if FastAPI isn't installed."""
    try:
        from fastapi import FastAPI, WebSocket
    except ImportError as exc:
        raise DashboardUnavailable(
            "FastAPI is not installed — run: pip install fastapi uvicorn"
        ) from exc

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

    @app.get("/api/cards")
    def _cards():
        return all_cards()

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
