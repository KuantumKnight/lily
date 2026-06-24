"""Logging for Lily — quiet on screen, detailed in data/lily.log.

Lily talks to you through the CLI; the log is for *us* (debugging, audit, agent
activity later). It rotates so it never grows unbounded.
"""

import logging
from logging.handlers import RotatingFileHandler

from .config import LOG_LEVEL, LOG_PATH

_configured = False


def get_logger(name: str = "lily") -> logging.Logger:
    """Return a logger that writes to the rotating log file."""
    global _configured
    root = logging.getLogger("lily")
    if not _configured:
        root.setLevel(LOG_LEVEL)
        handler = RotatingFileHandler(
            LOG_PATH, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
        )
        root.addHandler(handler)
        root.propagate = False
        _configured = True
    return logging.getLogger(name if name.startswith("lily") else f"lily.{name}")
