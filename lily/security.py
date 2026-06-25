"""Secret detection — scan text (and the repo) for credentials that shouldn't leak.

Pure regex detection (:func:`detect_secrets`) over common credential shapes — AWS keys,
private-key headers, provider tokens, and ``key = "…"`` assignments — plus a repo walk
(:func:`scan_repo`) that skips binaries and noise dirs. Findings are **masked by default**
so Lily can report "you have an AWS key in config.py:12" without echoing the secret. The
clipboard reader uses stdlib :mod:`tkinter` (no third-party dep) and degrades gracefully.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from .log import get_logger

log = get_logger("security")


class ClipboardUnavailable(RuntimeError):
    """Raised when the clipboard can't be read (no display / tkinter missing)."""


@dataclass
class Finding:
    kind: str
    masked: str
    line: int


# (name, pattern). Group 'val' (if present) is the sensitive value to mask; else group 0.
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("bearer token", re.compile(r"\bBearer\s+(?P<val>[A-Za-z0-9._\-]{20,})")),
    (
        "credential assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|token|password|passwd|pwd)\b\s*[=:]\s*"
            r"['\"]?(?P<val>[A-Za-z0-9_\-./+]{12,})['\"]?"
        ),
    ),
]


def mask(value: str) -> str:
    """Mask a secret, keeping a hint of its shape (first 4 / last 2 chars if long enough)."""
    value = value.strip().strip("'\"")
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 6)}{value[-2:]}"


def detect_secrets(text: str) -> list[Finding]:
    """Find likely secrets in ``text``. Returns masked findings with line numbers. Pure."""
    findings: list[Finding] = []
    for lineno, line in enumerate((text or "").splitlines(), 1):
        for kind, pattern in _PATTERNS:
            m = pattern.search(line)
            if not m:
                continue
            value = m.groupdict().get("val") or m.group(0)
            findings.append(Finding(kind=kind, masked=mask(value), line=lineno))
    return findings


_SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "data", ".idea", ".vscode"}
_MAX_BYTES = 1_000_000


def scan_repo(root) -> list[tuple[str, Finding]]:
    """Walk ``root`` and detect secrets in text files. Returns (relative_path, Finding)."""
    root = Path(root)
    results: list[tuple[str, Finding]] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        try:
            if path.stat().st_size > _MAX_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeDecodeError):
            continue  # binary or unreadable — skip
        for finding in detect_secrets(text):
            results.append((str(path.relative_to(root)), finding))
    return results


def read_clipboard() -> str:
    """Return the clipboard text via stdlib tkinter. Raises ClipboardUnavailable."""
    try:
        import tkinter
    except Exception as exc:  # tkinter not built / unavailable
        raise ClipboardUnavailable(f"tkinter unavailable: {exc}") from exc
    try:
        root = tkinter.Tk()
        root.withdraw()
        try:
            return root.clipboard_get()
        finally:
            root.destroy()
    except Exception as exc:  # no display, empty clipboard, etc.
        raise ClipboardUnavailable(f"could not read clipboard: {exc}") from exc
