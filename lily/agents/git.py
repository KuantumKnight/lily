"""The git agent — a weekly "what I shipped" digest from the commit history.

Deliberately *not* a streak/gamification feature (personal-use Lily favours healthy
signals): it summarises real output — how many commits, which files, churn, and the
busiest days — over a recent window. The log is fetched via a stable machine-readable
format and parsed by the pure :func:`parse_log`, so the parsing is fully testable
without a repo. The digest is announced on the bus as ``work.digest``.
"""

import datetime as _dt
import shutil

from .. import bus
from ..devtools import _run
from ..log import get_logger
from . import Agent, register

log = get_logger("git")

# Sentinel-prefixed header line per commit, followed by --numstat rows.
_SEP = "@@C@@"
_FORMAT = f"{_SEP}%H|%ad|%s"


def _git_available() -> bool:
    return shutil.which("git") is not None


def parse_log(raw: str) -> list[dict]:
    """Parse ``git log --numstat`` output (our sentinel format) into commit dicts. Pure."""
    commits: list[dict] = []
    current: dict | None = None
    for line in (raw or "").splitlines():
        if line.startswith(_SEP):
            payload = line[len(_SEP):]
            parts = payload.split("|", 2)
            if len(parts) != 3:
                continue
            sha, date, subject = parts
            weekday = ""
            try:
                weekday = _dt.date.fromisoformat(date).strftime("%A")
            except ValueError:
                pass
            current = {
                "hash": sha[:8],
                "date": date,
                "weekday": weekday,
                "subject": subject,
                "files": 0,
                "insertions": 0,
                "deletions": 0,
            }
            commits.append(current)
        elif current is not None and "\t" in line:
            cols = line.split("\t")
            if len(cols) >= 3:
                ins, dels = cols[0], cols[1]
                current["files"] += 1
                # binary files show as "-"; treat as zero churn
                current["insertions"] += int(ins) if ins.isdigit() else 0
                current["deletions"] += int(dels) if dels.isdigit() else 0
    return commits


def summarize(commits: list[dict]) -> dict:
    """Roll a list of commit dicts into digest totals. Pure."""
    by_day: dict[str, int] = {}
    insertions = deletions = files = 0
    for c in commits:
        by_day[c["weekday"] or c["date"]] = by_day.get(c["weekday"] or c["date"], 0) + 1
        insertions += c["insertions"]
        deletions += c["deletions"]
        files += c["files"]
    busiest = max(by_day, key=by_day.get) if by_day else ""
    return {
        "commits": len(commits),
        "files": files,
        "insertions": insertions,
        "deletions": deletions,
        "by_day": by_day,
        "busiest_day": busiest,
    }


def digest(days: int = 7) -> dict:
    """Collect and summarize the last ``days`` of commits. Returns a digest dict."""
    if not _git_available():
        return {"error": "git is not installed.", "commits": 0}
    days = max(1, min(int(days), 365))
    _, raw = _run(
        [
            "git", "log",
            f"--since={days} days ago",
            f"--pretty=format:{_FORMAT}",
            "--date=format:%Y-%m-%d",
            "--numstat",
        ]
    )
    summary = summarize(parse_log(raw))
    summary["days"] = days
    return summary


def _format(summary: dict) -> str:
    if summary.get("error"):
        return f"[error] {summary['error']}"
    if not summary.get("commits"):
        return f"Nothing shipped in the last {summary.get('days', 7)} days."
    lines = [
        f"In the last {summary['days']} days you shipped:",
        f"  • {summary['commits']} commits across {summary['files']} file changes",
        f"  • +{summary['insertions']} / -{summary['deletions']} lines",
    ]
    if summary.get("busiest_day"):
        lines.append(f"  • busiest day: {summary['busiest_day']}")
    return "\n".join(lines)


def _handle(query: str, messages: list) -> str:
    summary = digest(7)
    bus.publish("work.digest", summary)
    log.info("work digest: %s commits", summary.get("commits", 0))
    return _format(summary)


register(
    Agent(
        name="git",
        description="Summarizes what you shipped recently (commits, files, churn).",
        handler=_handle,
        triggers=("what i shipped", "what did i ship", "weekly digest", "what have i done", "what i've shipped"),
    )
)
