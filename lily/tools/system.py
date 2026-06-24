"""System telemetry — lets Lily report on the health of the machine she lives on."""

import os
import shutil
import subprocess
from collections.abc import Iterable

import psutil

from . import tool


def _gb(n: int) -> float:
    return round(n / (1024**3), 1)


def _temperature_lines() -> list[str]:
    """Best-effort temperature snapshot. Empty when the platform exposes no sensors."""
    try:
        sensors = psutil.sensors_temperatures(fahrenheit=False)
    except (AttributeError, OSError):
        return []

    lines: list[str] = []
    for name, entries in sensors.items():
        current = _max_current(entries)
        if current is None:
            continue
        label = (
            "CPU temp"
            if name.lower() in {"coretemp", "k10temp", "cpu_thermal"}
            else f"Temp {name}"
        )
        lines.append(f"{label}: {current:.0f}C")
    return lines[:3]


def _max_current(entries: Iterable) -> float | None:
    readings = [
        entry.current
        for entry in entries
        if getattr(entry, "current", None) is not None
    ]
    return max(readings) if readings else None


def _gpu_line() -> str | None:
    """Best-effort NVIDIA GPU snapshot via nvidia-smi. None if unavailable."""
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        out = subprocess.run(
            [
                exe,
                "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            util, used, total, temp = (
                x.strip() for x in out.stdout.strip().splitlines()[0].split(",")
            )
            return f"GPU: {util}% · VRAM {used}/{total} MB · {temp}C"
    except Exception:
        return None
    return None


@tool(
    description="Get a live snapshot of system health: CPU, memory, disk, battery, and GPU "
    "if available. Use whenever the user asks how their machine/computer/PC is doing."
)
def system_status() -> str:
    cpu = psutil.cpu_percent(interval=0.5)
    vm = psutil.virtual_memory()
    drive = os.environ.get("SystemDrive", "C:") + os.sep
    disk = psutil.disk_usage(drive)

    lines = [
        f"CPU: {cpu:.0f}% ({psutil.cpu_count(logical=True)} threads)",
        f"RAM: {_gb(vm.used)}/{_gb(vm.total)} GB ({vm.percent:.0f}%)",
        f"Disk {drive}: {_gb(disk.used)}/{_gb(disk.total)} GB ({disk.percent:.0f}%)",
    ]

    try:
        battery = psutil.sensors_battery()
    except (AttributeError, OSError):
        battery = None
    if battery is not None:
        plug = "charging" if battery.power_plugged else "on battery"
        lines.append(f"Battery: {battery.percent:.0f}% ({plug})")

    lines.extend(_temperature_lines())

    gpu = _gpu_line()
    if gpu:
        lines.append(gpu)

    return "\n".join(lines)
