"""Lily's attention mode — passive (quiet, waiting) vs active (full conversation).

Mode is the single switch the rest of the system reacts to: the resource manager
(E12) unloads heavy models in passive mode, the interrupt engine (E13) and
notification batching (E14) defend focus differently per mode. It is persisted in
the state store and announced on the bus as ``mode.changed`` whenever it flips.
"""

import time

from . import bus, memory
from .config import MODE_DEFAULT
from .log import get_logger

log = get_logger("mode")

MODE_PASSIVE = "passive"
MODE_ACTIVE = "active"
_VALID = {MODE_PASSIVE, MODE_ACTIVE}

# Last-known mode, so we degrade gracefully if the DB is briefly unavailable.
_cache = MODE_DEFAULT if MODE_DEFAULT in _VALID else MODE_PASSIVE


def current() -> str:
    """The current mode, falling back to the last known value on DB error."""
    global _cache
    try:
        _cache = memory.get_state("mode", _cache)
    except Exception as exc:  # DB locked/missing — keep serving last known
        log.warning("mode read failed, using cached %s: %s", _cache, exc)
    return _cache


def set_mode(mode: str, reason: str = "manual") -> bool:
    """Switch mode, persist it, and publish ``mode.changed``. False if invalid/no-op."""
    global _cache
    mode = (mode or "").strip().lower()
    if mode not in _VALID:
        return False
    if current() == mode:
        return False  # already there — don't spam the bus
    _cache = mode
    try:
        memory.set_state("mode", mode)
    except Exception as exc:
        log.warning("mode persist failed (continuing in-memory): %s", exc)
    log.info("mode -> %s (%s)", mode, reason)
    bus.publish("mode.changed", {"mode": mode, "reason": reason, "ts": time.time()})
    return True


def is_passive() -> bool:
    return current() == MODE_PASSIVE


def is_active() -> bool:
    return current() == MODE_ACTIVE
