"""Local runtime health diagnostics."""

import shutil
from importlib.metadata import PackageNotFoundError, version

from .first_run import REQUIRED_PACKAGES

COMMANDS = ("ollama", "age")


def report() -> str:
    lines = ["Runtime health:"]
    for package in REQUIRED_PACKAGES:
        lines.append(_package_line(package))
    for command in COMMANDS:
        lines.append(_command_line(command))
    return "\n".join(lines)


def _package_line(package: str) -> str:
    try:
        installed = version(package)
    except PackageNotFoundError:
        return f"[missing] package {package}"
    return f"[ok] package {package} {installed}"


def _command_line(command: str) -> str:
    path = shutil.which(command)
    return f"[ok] command {command}: {path}" if path else f"[missing] command {command}"
