"""Keyboard signals for push-to-talk and barge-in.

Uses the Windows console (``msvcrt``). On any platform without it, the helpers
degrade to no-ops so the voice loop keeps working (just without key interrupts).
"""


def _msvcrt():
    try:
        import msvcrt

        return msvcrt
    except ImportError:
        return None


def drain() -> None:
    """Discard any pending keystrokes so a stale key doesn't trigger an interrupt."""
    m = _msvcrt()
    if m is None:
        return
    try:
        while m.kbhit():
            m.getwch()
    except Exception:
        pass


def key_pressed() -> bool:
    """True if a key is waiting (and consume it). Used to barge in mid-sentence."""
    m = _msvcrt()
    if m is None:
        return False
    try:
        if m.kbhit():
            m.getwch()
            return True
    except Exception:
        pass
    return False


def wait_key() -> None:
    """Block until a key is pressed (push-to-talk gate). No-op without a console."""
    m = _msvcrt()
    if m is None:
        return
    try:
        drain()
        m.getwch()
    except Exception:
        pass
