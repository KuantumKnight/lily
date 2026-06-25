"""Developer shell helpers — Lily's hands on the local repo.

Thin, safe wrappers over ``git`` and the test runner so the dev agent (and its tools)
can inspect the project without shelling out ad-hoc. Every command runs with a timeout
in the repo root, never raises (failures come back as text + return code), and argument
lists are passed as lists — never string-interpolated — so there is no shell to inject
into. :func:`detect_failure` is a pure regex pass over captured output.
"""

import re
import shlex
import shutil
import subprocess

from .config import ROOT
from .log import get_logger

log = get_logger("devtools")

# Markers that a build/test run went wrong, scanned case-insensitively.
_FAILURE_RE = re.compile(
    r"\b(error|failed|failure|traceback|exception|assertionerror|"
    r"\d+\s+failed|fatal|cannot|not found)\b",
    re.IGNORECASE,
)

_DEFAULT_TIMEOUT = 120


def _run(cmd: list[str], timeout: int = _DEFAULT_TIMEOUT) -> tuple[int, str]:
    """Run ``cmd`` (a list) in the repo root. Returns (returncode, combined output)."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return 127, f"[error] command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"[error] timed out after {timeout}s: {shlex.join(cmd)}"
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, output.strip()


def _git_available() -> bool:
    return shutil.which("git") is not None


def git_status() -> str:
    if not _git_available():
        return "[error] git is not installed."
    _, out = _run(["git", "status", "--short", "--branch"])
    return out or "(clean working tree)"


def git_log(count: int = 5) -> str:
    if not _git_available():
        return "[error] git is not installed."
    count = max(1, min(int(count), 50))
    _, out = _run(["git", "log", f"-{count}", "--oneline", "--no-decorate"])
    return out or "(no commits)"


def run_tests(target: str = "") -> tuple[int, str]:
    """Run pytest (optionally scoped to ``target``). Returns (returncode, output)."""
    cmd = ["python", "-m", "pytest", "-q"]
    if target.strip():
        cmd += shlex.split(target, posix=False)
    return _run(cmd)


def detect_failure(output: str) -> bool:
    """True if ``output`` looks like it contains an error/failure. Pure."""
    return bool(_FAILURE_RE.search(output or ""))
