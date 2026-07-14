"""Dependency-light diagnostics for Lily's local runtime.

This module intentionally uses only the Python standard library at import time so
``python -m lily doctor`` can explain a broken installation before Lily's normal
dependencies are available.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import importlib.util
import json
import os
import shutil
import socket
import sys
import tempfile
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CORE_PACKAGES = (
    ("ollama", "ollama"),
    ("rich", "rich"),
    ("psutil", "psutil"),
    ("APScheduler", "apscheduler"),
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("wsproto", "wsproto"),
)

OPTIONAL_PACKAGES = (
    ("faster-whisper", "speech-to-text"),
    ("piper-tts", "speech output"),
    ("openwakeword", "wake word"),
    ("sounddevice", "microphone"),
    ("mss", "screen capture"),
    ("rapidocr-onnxruntime", "screen OCR"),
    ("pypdf", "PDF retrieval"),
)


@dataclass(frozen=True)
class Settings:
    config_path: Path
    config_error: str
    model: str
    embed_model: str
    vision_model: str
    ollama_host: str
    dashboard_host: str
    dashboard_port: int
    tts_voice: str


@dataclass(frozen=True)
class Check:
    status: str
    name: str
    detail: str
    fix: str = ""


def _value(data: dict, key: str, default):
    env = os.environ.get(f"LILY_{key.upper()}")
    return env if env is not None else data.get(key, default)


def load_settings(root: Path = ROOT) -> Settings:
    """Load only the settings diagnostics need, preserving config parse errors."""
    config_path = Path(os.environ.get("LILY_CONFIG", root / "lily.toml")).expanduser()
    data: dict = {}
    error = ""
    if config_path.exists():
        try:
            with config_path.open("rb") as handle:
                loaded = tomllib.load(handle)
            data = loaded.get("lily", loaded)
            if not isinstance(data, dict):
                error = "The [lily] configuration must be a TOML table."
                data = {}
        except (OSError, tomllib.TOMLDecodeError) as exc:
            error = str(exc)

    raw_port = _value(data, "dashboard_port", 8000)
    try:
        dashboard_port = int(raw_port)
    except (TypeError, ValueError):
        dashboard_port = -1
        error = error or f"dashboard_port must be an integer, got {raw_port!r}."

    return Settings(
        config_path=config_path,
        config_error=error,
        model=str(_value(data, "model", "qwen3:8b")),
        embed_model=str(_value(data, "embed_model", "nomic-embed-text")),
        vision_model=str(_value(data, "vision_model", "llava:7b")),
        ollama_host=str(_value(data, "ollama_host", "http://localhost:11434")).rstrip("/"),
        dashboard_host=str(_value(data, "dashboard_host", "127.0.0.1")),
        dashboard_port=dashboard_port,
        tts_voice=str(_value(data, "tts_voice", "")),
    )


def _python_check() -> Check:
    version = ".".join(map(str, sys.version_info[:3]))
    if sys.version_info >= (3, 11):
        return Check("pass", "Python", f"{version} ({Path(sys.executable)})")
    return Check(
        "fail",
        "Python",
        f"{version} is too old; Lily requires Python 3.11 or newer.",
        "Install Python 3.11+ and recreate .venv.",
    )


def _config_checks(settings: Settings) -> list[Check]:
    if settings.config_error:
        checks = [
            Check(
                "fail",
                "Configuration",
                f"Cannot use {settings.config_path}: {settings.config_error}",
                "Fix the TOML value or copy lily.example.toml to lily.toml again.",
            )
        ]
    else:
        source = str(settings.config_path) if settings.config_path.exists() else "built-in defaults"
        checks = [Check("pass", "Configuration", source)]

    parsed = urllib.parse.urlparse(settings.ollama_host)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        checks.append(
            Check(
                "fail",
                "Ollama URL",
                f"Invalid ollama_host: {settings.ollama_host!r}",
                "Use a URL such as http://localhost:11434.",
            )
        )
    elif parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        checks.append(
            Check(
                "warn",
                "Ollama privacy",
                f"Configured host is remote: {settings.ollama_host}",
                "Use localhost unless sending prompts to this host is intentional.",
            )
        )

    if settings.dashboard_host not in {"127.0.0.1", "localhost", "::1"}:
        checks.append(
            Check(
                "fail",
                "Dashboard binding",
                f"dashboard_host is {settings.dashboard_host!r}, not loopback-only.",
                "Set dashboard_host = \"127.0.0.1\" to keep Lily local.",
            )
        )
    if not 1 <= settings.dashboard_port <= 65535:
        checks.append(
            Check(
                "fail",
                "Dashboard port",
                f"Invalid port: {settings.dashboard_port}",
                "Choose a dashboard_port between 1 and 65535.",
            )
        )
    return checks


def _package_checks() -> list[Check]:
    missing_core = []
    broken_core = []
    versions = []
    for distribution, module in CORE_PACKAGES:
        try:
            package_version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            missing_core.append(distribution)
            continue
        try:
            importlib.import_module(module)
        except Exception as exc:
            broken_core.append(f"{distribution} ({exc})")
        else:
            versions.append(f"{distribution} {package_version}")

    checks = []
    if missing_core:
        checks.append(
            Check(
                "fail",
                "Core packages",
                "Missing: " + ", ".join(missing_core),
                "Run: python -m pip install -r requirements.txt",
            )
        )
    if broken_core:
        checks.append(
            Check(
                "fail",
                "Core imports",
                "Installed but unusable: " + ", ".join(broken_core),
                "Recreate .venv and reinstall requirements.txt.",
            )
        )
    if not missing_core and not broken_core:
        checks.append(Check("pass", "Core packages", ", ".join(versions)))

    missing_optional = []
    for distribution, feature in OPTIONAL_PACKAGES:
        try:
            importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            missing_optional.append(f"{distribution} ({feature})")
    if missing_optional:
        checks.append(
            Check(
                "warn",
                "Optional features",
                "Unavailable: " + ", ".join(missing_optional),
                "Install requirements.txt to enable every local modality.",
            )
        )
    else:
        checks.append(Check("pass", "Optional features", "All voice, vision, OCR, and PDF packages installed."))
    return checks


def _storage_check(root: Path) -> Check:
    data_dir = root / "data"
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix="lily-doctor-", dir=data_dir, delete=True):
            pass
    except OSError as exc:
        return Check(
            "fail",
            "Local storage",
            f"Cannot write to {data_dir}: {exc}",
            "Move Lily to a writable folder or correct the folder permissions.",
        )
    return Check("pass", "Local storage", f"Writable: {data_dir}")


def _port_check(settings: Settings) -> Check:
    if not 1 <= settings.dashboard_port <= 65535:
        return Check("fail", "Dashboard availability", "Skipped because the configured port is invalid.")
    family = socket.AF_INET6 if ":" in settings.dashboard_host else socket.AF_INET
    try:
        with socket.socket(family, socket.SOCK_STREAM) as probe:
            probe.bind((settings.dashboard_host, settings.dashboard_port))
    except OSError as exc:
        return Check(
            "warn",
            "Dashboard availability",
            f"{settings.dashboard_host}:{settings.dashboard_port} is already in use ({exc}).",
            "Stop the other process or choose a different dashboard_port.",
        )
    return Check("pass", "Dashboard availability", f"{settings.dashboard_host}:{settings.dashboard_port} is available.")


def _model_names(payload: dict) -> set[str]:
    names = set()
    if not isinstance(payload, dict):
        return names
    for item in payload.get("models", []):
        if isinstance(item, dict):
            name = item.get("name") or item.get("model")
            if name:
                names.add(str(name))
    return names


def _ollama_checks(settings: Settings, timeout: float) -> list[Check]:
    checks = []
    executable = shutil.which("ollama")
    if executable:
        checks.append(Check("pass", "Ollama command", executable))
    else:
        checks.append(
            Check(
                "warn",
                "Ollama command",
                "The ollama executable is not on PATH.",
                "Install Ollama or add it to PATH; an already-running service can still work.",
            )
        )

    parsed = urllib.parse.urlparse(settings.ollama_host)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return checks
    try:
        request = urllib.request.Request(
            f"{settings.ollama_host}/api/tags",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TypeError, ValueError) as exc:
        checks.append(
            Check(
                "fail",
                "Ollama service",
                f"Cannot reach {settings.ollama_host}: {exc}",
                "Start Ollama with: ollama serve",
            )
        )
        return checks

    checks.append(Check("pass", "Ollama service", f"Reachable at {settings.ollama_host}"))
    names = _model_names(payload)
    if settings.model in names:
        checks.append(Check("pass", "Chat model", settings.model))
    else:
        checks.append(
            Check(
                "fail",
                "Chat model",
                f"{settings.model!r} is not installed.",
                f"Run: ollama pull {settings.model}",
            )
        )
    for label, model in (("Embedding model", settings.embed_model), ("Vision model", settings.vision_model)):
        if model in names:
            checks.append(Check("pass", label, model))
        else:
            checks.append(Check("warn", label, f"{model!r} is not installed.", f"Run: ollama pull {model}"))
    return checks


def _audio_check() -> Check:
    if importlib.util.find_spec("sounddevice") is None:
        return Check(
            "warn",
            "Microphone",
            "sounddevice is not installed; text chat is unaffected.",
            "Install requirements.txt to enable voice input.",
        )
    try:
        sounddevice = importlib.import_module("sounddevice")
        device = sounddevice.query_devices(kind="input")
        name = device.get("name", "default input") if isinstance(device, dict) else str(device)
        return Check("pass", "Microphone", name)
    except Exception as exc:
        return Check(
            "warn",
            "Microphone",
            f"No usable default input device: {exc}",
            "Connect a microphone or select a Windows default recording device.",
        )


def _voice_check(settings: Settings, root: Path) -> Check:
    if not settings.tts_voice:
        return Check(
            "warn",
            "Lily voice",
            "No Piper voice is configured; text chat is ready.",
            "Set tts_voice to a downloaded .onnx voice when you want speech output.",
        )
    path = Path(settings.tts_voice).expanduser()
    if not path.is_absolute():
        path = root / path
    if path.is_file() and Path(f"{path}.json").is_file():
        return Check("pass", "Lily voice", str(path))
    return Check(
        "warn",
        "Lily voice",
        f"Voice model or metadata is missing: {path}",
        "Provide both the Piper .onnx file and its .onnx.json metadata file.",
    )


def run_checks(settings: Settings | None = None, root: Path = ROOT, timeout: float = 2.0) -> list[Check]:
    """Run diagnostics in stable display order."""
    settings = settings or load_settings(root)
    checks = [_python_check(), *_config_checks(settings), *_package_checks(), _storage_check(root)]
    checks.append(_port_check(settings))
    checks.extend(_ollama_checks(settings, timeout))
    checks.extend((_audio_check(), _voice_check(settings, root)))
    return checks


def _render_text(checks: list[Check]) -> str:
    icons = {"pass": "[PASS]", "warn": "[WARN]", "fail": "[FAIL]"}
    lines = ["Lily doctor", "==========="]
    for check in checks:
        lines.append(f"{icons[check.status]} {check.name}: {check.detail}")
        if check.fix:
            lines.append(f"       Fix: {check.fix}")
    passed = sum(check.status == "pass" for check in checks)
    warned = sum(check.status == "warn" for check in checks)
    failed = sum(check.status == "fail" for check in checks)
    lines.extend(("", f"Summary: {passed} passed, {warned} warnings, {failed} failed."))
    lines.append("Lily is ready for core use." if failed == 0 else "Lily is not ready yet; fix the failed checks above.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check whether Lily is ready to run.")
    parser.add_argument("--json", action="store_true", help="emit machine-readable diagnostics")
    parser.add_argument("--timeout", type=float, default=2.0, help="Ollama connection timeout in seconds")
    args = parser.parse_args(argv)
    checks = run_checks(timeout=max(0.1, args.timeout))
    if args.json:
        print(json.dumps({"checks": [asdict(check) for check in checks]}, indent=2))
    else:
        print(_render_text(checks))
    return 1 if any(check.status == "fail" for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
