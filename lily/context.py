"""Context fusion: local clues about what the user is doing now."""

import ctypes
import platform
from ctypes import wintypes

from . import devtools, memory, ocr, vision


def snapshot(include_vision: bool = True, monitor: int = 1) -> str:
    """Combine active window, git state, project memory, and optional screen senses."""
    sections = [
        ("Active window", active_window_title() or "Unavailable"),
        ("Active project", memory.active_project() or "None"),
        ("Git", devtools.git_status()),
    ]

    screen_text = _try_screen_text(monitor)
    if screen_text:
        sections.append(("Screen text", screen_text))

    if include_vision:
        visual = _try_visual_summary(monitor)
        if visual:
            sections.append(("Visual summary", visual))

    return "\n\n".join(f"{title}:\n{body}" for title, body in sections if body)


def active_window_title() -> str:
    """Best-effort active window title. Currently implemented for Windows."""
    if platform.system() != "Windows":
        return ""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return f"{buffer.value} (pid {pid.value})"
    except Exception:
        return ""


def _try_screen_text(monitor: int) -> str:
    try:
        return ocr.read_text(monitor=monitor)
    except ocr.OCRUnavailable as exc:
        return f"[unavailable] {exc}"


def _try_visual_summary(monitor: int) -> str:
    prompt = (
        "Summarize what the user appears to be doing from this screenshot. "
        "Mention visible errors, terminals, editors, browser pages, and likely next actions."
    )
    try:
        return vision.describe_image(prompt=prompt, monitor=monitor)
    except vision.VisionUnavailable as exc:
        return f"[unavailable] {exc}"
