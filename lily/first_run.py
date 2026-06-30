"""First-run checks for Lily's local runtime."""

from importlib.metadata import PackageNotFoundError, version

import ollama

from .config import MODEL, OLLAMA_HOST
from .log import get_logger

log = get_logger("first_run")

REQUIRED_PACKAGES = (
    "ollama",
    "rich",
    "psutil",
    "apscheduler",
    "faster-whisper",
    "piper-tts",
    "openwakeword",
    "sounddevice",
    "mss",
)


def check_runtime() -> list[str]:
    """Return human-readable setup warnings. Never raises."""
    warnings: list[str] = []
    warnings.extend(_check_packages())
    warnings.extend(_check_ollama_model())
    return warnings


def _check_packages() -> list[str]:
    warnings: list[str] = []
    for package in REQUIRED_PACKAGES:
        try:
            version(package)
        except PackageNotFoundError:
            warnings.append(
                f"Missing Python package '{package}'. Run: pip install -r requirements.txt"
            )
    return warnings


def _check_ollama_model() -> list[str]:
    client = ollama.Client(host=OLLAMA_HOST)
    try:
        response = client.list()
    except Exception as exc:
        log.warning("ollama setup check failed: %s", exc)
        return [f"Cannot reach Ollama at {OLLAMA_HOST}. Start it with: ollama serve"]

    models = _model_names(response)
    if MODEL not in models:
        return [f"Model '{MODEL}' is not pulled. Run: ollama pull {MODEL}"]
    return []


def _model_names(response) -> set[str]:
    raw_models = response.get("models", []) if isinstance(response, dict) else response.models
    names: set[str] = set()
    for item in raw_models:
        if isinstance(item, dict):
            name = item.get("name") or item.get("model")
        else:
            name = getattr(item, "name", None) or getattr(item, "model", None)
        if name:
            names.add(str(name))
    return names
