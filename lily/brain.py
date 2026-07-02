"""Lily's brain — a thin streaming wrapper over a local Ollama model."""

from collections.abc import Iterator

from .config import EMBED_MODEL, MODEL, OLLAMA_HOST
from .log import get_logger

log = get_logger("brain")


class BrainOffline(Exception):
    """Raised when the local model can't be reached or used."""


def _client():
    try:
        import ollama
    except ImportError as exc:
        raise BrainOffline(
            "Python package 'ollama' is not installed. Run: pip install -r requirements.txt"
        ) from exc
    return ollama, ollama.Client(host=OLLAMA_HOST)


def embed(text: str) -> list[float]:
    """Return an embedding vector for ``text`` via the local embedding model.

    Raises BrainOffline if Ollama is unreachable or the embed model isn't pulled.
    """
    ollama, client = _client()
    try:
        response = client.embed(model=EMBED_MODEL, input=text)
        vectors = response.get("embeddings") or []
        return list(vectors[0]) if vectors else []
    except AttributeError:
        # Older ollama clients expose embeddings() returning a single vector.
        response = client.embeddings(model=EMBED_MODEL, prompt=text)
        return list(response.get("embedding") or [])
    except ollama.ResponseError as exc:
        if "not found" in str(exc).lower():
            raise BrainOffline(
                f"Embedding model '{EMBED_MODEL}' isn't pulled. Run:  ollama pull {EMBED_MODEL}"
            ) from exc
        raise BrainOffline(str(exc)) from exc
    except Exception as exc:
        raise BrainOffline(
            f"Can't reach Ollama at {OLLAMA_HOST} for embeddings. Is it running?"
        ) from exc


def _prepare(messages: list[dict]) -> list[dict]:
    """Model-specific tweaks. Qwen3 emits <think> blocks unless told not to."""
    if "qwen3" in MODEL and messages and messages[0]["role"] == "system":
        messages = list(messages)
        messages[0] = {
            "role": "system",
            "content": messages[0]["content"] + "\n\n/no_think",
        }
    return messages


def chat_once(messages: list[dict], tools: list[dict] | None = None):
    """One non-streamed chat turn. Returns the model's message (may contain tool_calls).

    Raises BrainOffline on failure.
    """
    ollama, client = _client()
    try:
        return client.chat(model=MODEL, messages=_prepare(messages), tools=tools)["message"]
    except ollama.ResponseError as exc:
        if "not found" in str(exc).lower():
            log.error("model %s not pulled: %s", MODEL, exc)
            raise BrainOffline(
                f"Model '{MODEL}' isn't pulled. Run:  ollama pull {MODEL}"
            ) from exc
        log.error("ollama response error: %s", exc)
        raise BrainOffline(str(exc)) from exc
    except Exception as exc:
        log.error("cannot reach ollama at %s: %s", OLLAMA_HOST, exc)
        raise BrainOffline(
            f"Can't reach Ollama at {OLLAMA_HOST}. Is it running?  (ollama serve)"
        ) from exc


def stream_chat(messages: list[dict]) -> Iterator[str]:
    """Yield Lily's reply token-by-token. Raises BrainOffline on failure."""
    ollama, client = _client()
    try:
        for chunk in client.chat(model=MODEL, messages=_prepare(messages), stream=True):
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
