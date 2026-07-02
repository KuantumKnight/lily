"""Opt-in cloud-burst reasoning for hard queries only."""

import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlparse

from .config import (
    CLOUD_BURST_ENABLED,
    CLOUD_BURST_KEY_ENV,
    CLOUD_BURST_MODEL,
    CLOUD_BURST_URL,
)


class CloudBurstUnavailable(RuntimeError):
    """Raised when cloud-burst reasoning is disabled, unconfigured, or unavailable."""


_HARD_MARKERS = (
    "prove",
    "architecture",
    "tradeoff",
    "debug this complex",
    "root cause",
    "security review",
    "design a plan",
    "multi-step",
    "hard query",
)


def is_hard(query: str) -> bool:
    lowered = query.lower()
    return len(query) > 800 or any(marker in lowered for marker in _HARD_MARKERS)


def ask(query: str, context: str = "", force: bool = False) -> str:
    """Send a hard query to a configured frontier API, only when explicitly enabled."""
    if not CLOUD_BURST_ENABLED:
        raise CloudBurstUnavailable("cloud burst is disabled; set cloud_burst_enabled = true")
    if not force and not is_hard(query):
        raise CloudBurstUnavailable("query does not look hard enough for cloud burst")
    if not CLOUD_BURST_URL:
        raise CloudBurstUnavailable("set cloud_burst_url to an OpenAI-compatible endpoint")
    _validate_url(CLOUD_BURST_URL)
    key = os.environ.get(CLOUD_BURST_KEY_ENV) if CLOUD_BURST_KEY_ENV else ""
    if not key:
        raise CloudBurstUnavailable(f"set API key in environment variable {CLOUD_BURST_KEY_ENV}")

    payload = {
        "model": CLOUD_BURST_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Lily's opt-in cloud reasoning fallback. Handle only the "
                    "hard part of the task. Be concise and avoid requesting private data."
                ),
            },
            {"role": "user", "content": _prompt(query, context)},
        ],
    }
    request = urllib.request.Request(
        CLOUD_BURST_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise CloudBurstUnavailable(f"cloud API error {exc.code}: {body}") from exc
    except Exception as exc:
        raise CloudBurstUnavailable(f"cloud API unavailable: {exc}") from exc

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise CloudBurstUnavailable("cloud API response did not include a chat reply") from exc


def _prompt(query: str, context: str) -> str:
    if not context.strip():
        return query
    return f"Local context:\n{context.strip()}\n\nHard query:\n{query.strip()}"


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme == "https":
        return
    if parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}:
        return
    raise CloudBurstUnavailable("cloud_burst_url must use https unless it is localhost")
