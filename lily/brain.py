"""Lily's brain — a thin streaming wrapper over a local Ollama model."""

from collections.abc import Iterator

import ollama

from .config import MODEL, OLLAMA_HOST
from .log import get_logger

log = get_logger("brain")
_client = ollama.Client(host=OLLAMA_HOST)


class BrainOffline(Exception):
    """Raised when the local model can't be reached or used."""


def _prepare(messages: list[dict]) -> list[dict]:
    """Model-specific tweaks. Qwen3 emits <think> blocks unless told not to."""
    if "qwen3" in MODEL and messages and messages[0]["role"] == "system":
        messages = list(messages)
        messages[0] = {
            "role": "system",
            "content": messages[0]["content"] + "\n\n/no_think",
        }
    return messages


def stream_chat(messages: list[dict]) -> Iterator[str]:
    """Yield Lily's reply token-by-token. Raises BrainOffline on failure."""
    try:
        for chunk in _client.chat(model=MODEL, messages=_prepare(messages), stream=True):
            piece = chunk.get("message", {}).get("content", "")
            if piece:
                yield piece
    except ollama.ResponseError as exc:
        if "not found" in str(exc).lower():
            log.error("model %s not pulled: %s", MODEL, exc)
            raise BrainOffline(
                f"Model '{MODEL}' isn't pulled. Run:  ollama pull {MODEL}"
            ) from exc
        log.error("ollama response error: %s", exc)
        raise BrainOffline(str(exc)) from exc
    except Exception as exc:  # connection refused, timeout, transport errors...
        log.error("cannot reach ollama at %s: %s", OLLAMA_HOST, exc)
        raise BrainOffline(
            f"Can't reach Ollama at {OLLAMA_HOST}. Is it running?  (ollama serve)"
        ) from exc
