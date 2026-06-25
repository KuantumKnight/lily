"""Resource manager — keep passive mode light by unloading heavy local models.

The STT model, TTS voice, and wake model are lazy-loaded singletons that hold real
RAM/VRAM. When Lily drops to passive mode (E11) this manager unloads them; they
reload on next demand. It subscribes to ``mode.changed`` so the policy is automatic,
and exposes load/unload/status for manual control via tools.
"""

import gc

from . import bus, stt, tts, wake
from .config import RESOURCE_AUTOLOAD
from .log import get_logger

log = get_logger("resources")

# name -> (is_loaded probe, unload fn, lazy loader fn)
_MODELS = {
    "stt": (stt.is_loaded, stt.unload, stt._load_model),
    "tts": (tts.is_loaded, tts.unload, tts._load_voice),
    "wake": (wake.is_loaded, wake.unload, wake._load_model),
}


def status() -> dict:
    """Which heavy models are currently resident in memory."""
    return {name: probe() for name, (probe, _, _) in _MODELS.items()}


def unload(name: str) -> str:
    entry = _MODELS.get(name)
    if entry is None:
        return f"[error] unknown model '{name}'"
    _, unload_fn, _ = entry
    was = entry[0]()
    unload_fn()
    return f"{name}: {'unloaded' if was else 'already free'}"


def load(name: str) -> str:
    entry = _MODELS.get(name)
    if entry is None:
        return f"[error] unknown model '{name}'"
    _, _, loader = entry
    try:
        loader()
        return f"{name}: loaded"
    except Exception as exc:  # model deps/voice missing — report, don't crash
        return f"[error] {name} load failed: {exc}"


def unload_all() -> list[str]:
    """Unload every loaded model. Returns the names actually freed."""
    freed = [name for name, (probe, _, _) in _MODELS.items() if probe()]
    for name in freed:
        _MODELS[name][1]()
    if freed:
        gc.collect()
        log.info("freed on passive: %s", ", ".join(freed))
    return freed


def _on_mode_changed(topic: str, payload: object) -> None:
    if not RESOURCE_AUTOLOAD:
        return
    if isinstance(payload, dict) and payload.get("mode") == "passive":
        unload_all()


def init() -> None:
    """Wire automatic unload-on-passive. Idempotent enough for a single startup call."""
    bus.subscribe("mode.changed", _on_mode_changed)
    log.info("resource manager active (autoload=%s)", RESOURCE_AUTOLOAD)
