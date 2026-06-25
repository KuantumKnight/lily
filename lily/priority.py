"""Interrupt priority engine — decide whether an interruption earns Lily's attention.

Four levels (low → emergency) are weighed against the current mode (E11): emergencies
and high-priority always surface; in active mode normal traffic surfaces and low gets
batched (E14); in passive mode Lily defends focus harder — normal is batched and low is
dropped. :func:`decide` is pure and fully testable; :func:`dispatch` adds a bus event.
"""

from dataclasses import dataclass
from enum import IntEnum

from . import bus
from . import mode as mode_module
from .config import INTERRUPT_ACTIVE_THRESHOLD, INTERRUPT_DROP_BELOW
from .log import get_logger

log = get_logger("priority")


class Priority(IntEnum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    EMERGENCY = 3


@dataclass
class Decision:
    action: str  # 'surface' | 'defer' | 'drop'
    reason: str


def coerce(value) -> Priority:
    """Best-effort parse of a name/number/Priority into a Priority (defaults NORMAL)."""
    if isinstance(value, Priority):
        return value
    if isinstance(value, int):
        try:
            return Priority(value)
        except ValueError:
            return Priority.NORMAL
    try:
        return Priority[str(value).strip().upper()]
    except KeyError:
        return Priority.NORMAL


def decide(priority, current_mode: str | None = None) -> Decision:
    """Pure routing decision for an interruption of ``priority`` in ``current_mode``."""
    pri = coerce(priority)
    active_mode = current_mode or mode_module.current()

    if pri >= Priority.HIGH:
        return Decision("surface", f"{pri.name} surfaces in any mode")

    if active_mode == mode_module.MODE_ACTIVE:
        if pri >= coerce(INTERRUPT_ACTIVE_THRESHOLD):
            return Decision("surface", "active mode, meets threshold")
        return Decision("defer", "active mode, low priority — batch it")

    # passive: defend focus
    if pri >= coerce(INTERRUPT_DROP_BELOW):
        return Decision("defer", "passive mode — batch for later")
    return Decision("drop", "passive mode, below drop threshold")


def dispatch(content: str, priority="normal", source: str = "") -> Decision:
    """Decide and announce an interruption on the bus. Returns the Decision."""
    decision = decide(priority)
    bus.publish(
        "interrupt.raised",
        {
            "content": content,
            "priority": coerce(priority).name,
            "action": decision.action,
            "reason": decision.reason,
            "source": source,
        },
    )
    log.info("interrupt [%s] %s -> %s", coerce(priority).name, source or "?", decision.action)
    return decision
