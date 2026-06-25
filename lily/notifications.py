"""Notification batching — hold quiet notifications until Lily is actually listening.

Reuses the four-level :class:`~lily.priority.Priority` from E13: HIGH and EMERGENCY
notifications bypass the queue and surface immediately; NORMAL and LOW are batched and
held until Lily next enters active mode (E11), at which point the whole batch flushes at
once. This keeps passive mode quiet without ever swallowing something urgent.

Surfacing is announced on the bus as ``notification.surfaced`` so any front-end (the CLI,
a future dashboard) can render the batch; queuing publishes ``notification.queued``.
"""

import threading
import time
from dataclasses import dataclass

from . import bus
from . import mode as mode_module
from .log import get_logger
from .priority import Priority, coerce

log = get_logger("notifications")


@dataclass
class Notification:
    content: str
    priority: str  # Priority name, e.g. "NORMAL"
    source: str
    ts: float


_lock = threading.RLock()
_queue: list[Notification] = []


def _payload(note: Notification) -> dict:
    return {
        "content": note.content,
        "priority": note.priority,
        "source": note.source,
        "ts": note.ts,
    }


def _surface(notes: list[Notification], reason: str) -> None:
    bus.publish(
        "notification.surfaced",
        {"notifications": [_payload(n) for n in notes], "reason": reason},
    )
    log.info("surfaced %d notification(s) (%s)", len(notes), reason)


def enqueue(content: str, priority="normal", source: str = "", ts: float | None = None) -> Notification:
    """Queue a notification. HIGH/EMERGENCY surface at once; NORMAL/LOW are batched."""
    pri = coerce(priority)
    note = Notification(content, pri.name, source, time.time() if ts is None else ts)
    if pri >= Priority.HIGH:
        _surface([note], reason=f"{pri.name} bypasses the queue")
        return note
    with _lock:
        _queue.append(note)
    log.info("queued notification [%s] from %s", pri.name, source or "?")
    bus.publish("notification.queued", _payload(note))
    return note


def pending() -> list[Notification]:
    """A snapshot of the currently-batched notifications."""
    with _lock:
        return list(_queue)


def flush(reason: str = "manual") -> list[Notification]:
    """Surface and clear the whole batch. Returns what was flushed (empty if none)."""
    with _lock:
        if not _queue:
            return []
        batch = list(_queue)
        _queue.clear()
    _surface(batch, reason=reason)
    return batch


def clear() -> None:
    """Drop the batch without surfacing it (mainly for tests)."""
    with _lock:
        _queue.clear()


def _on_mode_changed(topic: str, payload: object) -> None:
    if isinstance(payload, dict) and payload.get("mode") == mode_module.MODE_ACTIVE:
        flush(reason="entered active mode")


_subscribed = False


def init() -> None:
    """Wire up the auto-flush on entering active mode (idempotent)."""
    global _subscribed
    if _subscribed:
        return
    bus.subscribe("mode.changed", _on_mode_changed)
    _subscribed = True
    log.debug("notification batching armed")
