"""Central configuration for Lily.

Precedence (highest first):  environment variable  >  config file  >  built-in default.

Config file is TOML, looked up at ``lily.toml`` in the repo root (override the path with
``LILY_CONFIG``). See ``lily.example.toml`` for the format. Everything has a sane default,
so Lily runs with no config file at all.
"""

import os
import tomllib
from pathlib import Path

# Repo root = parent of the `lily` package directory.
ROOT = Path(__file__).resolve().parent.parent

# Runtime data (her memory + logs). Gitignored — never leaves the machine.
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "lily.db"
LOG_PATH = DATA_DIR / "lily.log"

CONFIG_PATH = Path(os.environ.get("LILY_CONFIG", ROOT / "lily.toml"))

_DEFAULTS: dict = {
    "model": "qwen3:8b",
    "embed_model": "nomic-embed-text",
    "ollama_host": "http://localhost:11434",
    "context_window": 20,
    "log_level": "INFO",
    "stt_model": "base",
    "stt_device": "cpu",
    "stt_compute_type": "int8",
    "tts_voice": "",
    "tts_autospeak": False,
    "wake_model": "hey_jarvis",
    "wake_threshold": 0.5,
    "mic_silence_threshold": 500,
    "mic_silence_seconds": 1.0,
    "mic_max_seconds": 15.0,
    "barge_in": True,
    "push_to_talk": False,
    "mode": "passive",
    "resource_autoload": True,
    "interrupt_active_threshold": "NORMAL",
    "interrupt_drop_below": "NORMAL",
    "calendar_ics_path": "",
    "calendar_prep_minutes": 15,
}


def _load_file() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "rb") as fh:
            data = tomllib.load(fh)
        # Accept either a top-level table or a [lily] section.
        return data.get("lily", data)
    return {}


_FILE = _load_file()


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _get(key: str, cast=str):
    """Resolve one setting through the precedence chain."""
    env = os.environ.get("LILY_" + key.upper())
    if env is not None:
        return cast(env)
    if key in _FILE:
        return cast(_FILE[key])
    return _DEFAULTS[key]


MODEL = _get("model")
EMBED_MODEL = _get("embed_model")
OLLAMA_HOST = _get("ollama_host")
CONTEXT_WINDOW = _get("context_window", int)
LOG_LEVEL = _get("log_level")
STT_MODEL = _get("stt_model")
STT_DEVICE = _get("stt_device")
STT_COMPUTE_TYPE = _get("stt_compute_type")
TTS_VOICE = _get("tts_voice")
TTS_AUTOSPEAK = _get("tts_autospeak", _to_bool)
WAKE_MODEL = _get("wake_model")
WAKE_THRESHOLD = _get("wake_threshold", float)
MIC_SILENCE_THRESHOLD = _get("mic_silence_threshold", float)
MIC_SILENCE_SECONDS = _get("mic_silence_seconds", float)
MIC_MAX_SECONDS = _get("mic_max_seconds", float)
BARGE_IN = _get("barge_in", _to_bool)
PUSH_TO_TALK = _get("push_to_talk", _to_bool)
MODE_DEFAULT = _get("mode")
RESOURCE_AUTOLOAD = _get("resource_autoload", _to_bool)
INTERRUPT_ACTIVE_THRESHOLD = _get("interrupt_active_threshold")
INTERRUPT_DROP_BELOW = _get("interrupt_drop_below")
CALENDAR_ICS_PATH = _get("calendar_ics_path")
CALENDAR_PREP_MINUTES = _get("calendar_prep_minutes", int)
