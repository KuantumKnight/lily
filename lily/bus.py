"""Lily's event bus — in-process pub/sub so agents can react to what's happening.

Agents subscribe to topics (``user.message``, ``lily.reply``, ``reminder.fired``,
…) and publish their own. A subscription to ``"*"`` receives every event. Delivery
is synchronous and thread-safe; a subscriber that raises is logged and skipped so
it can never take down the publisher or starve other subscribers.
"""

import threading
from collections.abc import Callable

from .log import get_logger

log = get_logger("bus")

WILDCARD = "*"
# callback signature: (topic, payload) -> None
Subscriber = Callable[[str, object], None]

_lock = threading.RLock()
_subs: dict[str, list[Subscriber]] = {}


def subscribe(topic: str, callback: Subscriber) -> Callable[[], None]:
    """Register ``callback`` for ``topic`` (or ``"*"`` for all). Returns an unsubscribe fn."""
    with _lock:
        _subs.setdefault(topic, []).append(callback)
    log.debug("subscribed to %s", topic)

    def _unsub() -> None:
        unsubscribe(topic, callback)

    return _unsub


def unsubscribe(topic: str, callback: Subscriber) -> None:
    with _lock:
        subscribers = _subs.get(topic)
        if subscribers and callback in subscribers:
            subscribers.remove(callback)


def publish(topic: str, payload: object = None) -> int:
    """Deliver ``payload`` to ``topic`` subscribers (plus wildcards). Returns count delivered."""
    with _lock:
        targets = list(_subs.get(topic, [])) + list(_subs.get(WILDCARD, []))
    delivered = 0
    for callback in targets:
        try:
            callback(topic, payload)
            delivered += 1
        except Exception as exc:  # one bad subscriber must not break the rest
            log.error("subscriber for %s failed: %s", topic, exc)
    log.debug("published %s -> %d subscriber(s)", topic, delivered)
    return delivered


def clear() -> None:
    """Drop all subscriptions (mainly for tests)."""
    with _lock:
        _subs.clear()
