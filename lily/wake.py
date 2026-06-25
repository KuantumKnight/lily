"""Wake-word detection via openWakeWord — listen for Lily's name.

openWakeWord ships no pretrained "Lily" model, so ``wake_model`` defaults to the
bundled ``hey_jarvis``. Point it at a custom ``.onnx``/``.tflite`` to use a real
"Lily" model (train one with the openWakeWord tooling, then set ``wake_model``).
"""

from .config import WAKE_MODEL, WAKE_THRESHOLD
from .log import get_logger

log = get_logger("wake")

SAMPLE_RATE = 16000
FRAME_SIZE = 1280  # 80ms at 16kHz — openWakeWord's expected chunk
_MODEL = None


class WakeUnavailable(Exception):
    """Raised when wake-word dependencies, models, or the microphone are unavailable."""


def _is_path(value: str) -> bool:
    return value.endswith((".onnx", ".tflite")) or "/" in value or "\\" in value


def _load_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    try:
        from openwakeword.model import Model
        from openwakeword.utils import download_models
    except ImportError as exc:
        raise WakeUnavailable(
            "openwakeword is not installed. Run: pip install -r requirements.txt"
        ) from exc

    framework = "tflite" if WAKE_MODEL.endswith(".tflite") else "onnx"
    try:
        if _is_path(WAKE_MODEL):
            download_models([])  # base melspectrogram + embedding models
        else:
            download_models([WAKE_MODEL])
        log.info("loading wake model=%s framework=%s", WAKE_MODEL, framework)
        _MODEL = Model(wakeword_models=[WAKE_MODEL], inference_framework=framework)
    except Exception as exc:  # download/model errors → graceful degrade
        raise WakeUnavailable(f"could not load wake model '{WAKE_MODEL}': {exc}") from exc
    return _MODEL


def is_loaded() -> bool:
    return _MODEL is not None


def unload() -> None:
    """Release the wake model so its RAM can be reclaimed; reloads lazily on next use."""
    global _MODEL
    if _MODEL is not None:
        _MODEL = None
        log.info("wake model unloaded")


def listen_for_wake(on_wake, stop_event=None) -> None:
    """Stream the microphone and call ``on_wake(name, score)`` when the word fires.

    Blocks until ``stop_event`` is set (or forever). ``on_wake`` returning a truthy
    value stops the loop — handy for "wake once, then act".
    """
    try:
        import numpy as np
        import sounddevice as sd
    except ImportError as exc:
        raise WakeUnavailable(
            "sounddevice/numpy not installed. Run: pip install -r requirements.txt"
        ) from exc

    model = _load_model()
    try:
        stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=FRAME_SIZE
        )
    except Exception as exc:
        raise WakeUnavailable(f"no usable microphone: {exc}") from exc

    with stream:
        while stop_event is None or not stop_event.is_set():
            data, _ = stream.read(FRAME_SIZE)
            frame = np.frombuffer(data, dtype=np.int16)
            scores = model.predict(frame)
            for name, score in scores.items():
                if score >= WAKE_THRESHOLD:
                    log.info("wake word detected: %s (%.2f)", name, score)
                    model.reset()  # clear buffer so one utterance fires once
                    if on_wake(name, float(score)):
                        return
