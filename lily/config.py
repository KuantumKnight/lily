"""Central configuration for Lily. Override anything via environment variables."""

import os
from pathlib import Path

# Repo root = parent of the `lily` package directory.
ROOT = Path(__file__).resolve().parent.parent

# Runtime data (her memory). Gitignored — never leaves the machine.
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "lily.db"

# Brain
OLLAMA_HOST = os.environ.get("LILY_OLLAMA_HOST", "http://localhost:11434")
MODEL = os.environ.get("LILY_MODEL", "qwen3:8b")

# How many recent messages to feed back as conversational context.
CONTEXT_WINDOW = int(os.environ.get("LILY_CONTEXT_WINDOW", "20"))
