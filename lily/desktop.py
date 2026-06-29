"""Windows desktop shell for Lily.

This is intentionally small: it starts Lily's local dashboard, opens the browser UI,
and can launch the full CLI in a separate terminal. The window minimizes normally to
the Windows taskbar; closing the window also minimizes it so Lily stays available.
Use the Quit button to exit the desktop shell.
"""

import subprocess
import sys
import threading
import webbrowser
from tkinter import BOTH, LEFT, X, Button, Frame, Label, StringVar, Tk, messagebox, ttk

from . import dashboard, first_run, tools
from .config import DASHBOARD_HOST, DASHBOARD_PORT, MODEL, ROOT
from .log import get_logger

log = get_logger("desktop")


class LilyDesktop:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("Lily")
        self.root.geometry("520x300")
        self.root.minsize(460, 260)
        self.root.protocol("WM_DELETE_WINDOW", self.minimize)

        self.status = StringVar(value="Lily desktop is ready.")
        self.setup = StringVar(value="Checking setup...")
        self.dashboard_state = StringVar(value="Dashboard: stopped")
        self.dashboard_thread: threading.Thread | None = None

        self._build_ui()
        self.root.after(100, self.refresh_setup)

    @property
    def dashboard_url(self) -> str:
        return f"http://{DASHBOARD_HOST}:{DASHBOARD_PORT}"

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill=BOTH, expand=True)

        ttk.Label(outer, text="Lily", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text=f"Local-first assistant | brain: {MODEL}",
            foreground="#555555",
        ).pack(anchor="w", pady=(2, 12))

        ttk.Label(outer, textvariable=self.dashboard_state).pack(anchor="w")
        ttk.Label(outer, textvariable=self.setup, wraplength=470).pack(anchor="w", pady=(4, 12))

        buttons = Frame(outer)
        buttons.pack(fill=X, pady=(4, 12))
        Button(buttons, text="Start Dashboard", command=self.start_dashboard).pack(side=LEFT, padx=(0, 8))
        Button(buttons, text="Open Dashboard", command=self.open_dashboard).pack(side=LEFT, padx=(0, 8))
        Button(buttons, text="Open CLI", command=self.open_cli).pack(side=LEFT, padx=(0, 8))
        Button(buttons, text="Minimize", command=self.minimize).pack(side=LEFT, padx=(0, 8))
        Button(buttons, text="Quit", command=self.quit).pack(side=LEFT)

        ttk.Separator(outer).pack(fill=X, pady=(4, 12))
        ttk.Label(outer, textvariable=self.status, wraplength=470).pack(anchor="w")
        ttk.Label(
            outer,
            text="Closing this window minimizes it to the taskbar. Use Quit to close Lily Desktop.",
            foreground="#666666",
            wraplength=470,
        ).pack(anchor="w", pady=(12, 0))

    def refresh_setup(self) -> None:
        tools.load_builtins()
        warnings = first_run.check_runtime()
        if warnings:
            self.setup.set("Setup: " + " | ".join(warnings))
        else:
            self.setup.set("Setup: ready")
        self.status.set(f"Tools loaded: {len(tools.schemas() or [])}")

    def start_dashboard(self) -> None:
        if self.dashboard_thread is not None and self.dashboard_thread.is_alive():
            self.status.set(f"Dashboard is already running at {self.dashboard_url}")
            return
        try:
            self.dashboard_thread = dashboard.start_in_thread()
        except dashboard.DashboardUnavailable as exc:
            messagebox.showerror("Dashboard unavailable", str(exc))
            return
        self.dashboard_state.set(f"Dashboard: running at {self.dashboard_url}")
        self.status.set("Dashboard started.")

    def open_dashboard(self) -> None:
        self.start_dashboard()
        webbrowser.open(self.dashboard_url)
        self.status.set(f"Opened {self.dashboard_url}")

    def open_cli(self) -> None:
        python = ROOT / ".venv" / "Scripts" / "python.exe"
        if not python.exists():
            python = sys.executable
        creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        subprocess.Popen(
            [str(python), "-m", "lily"],
            cwd=str(ROOT),
            creationflags=creationflags,
        )
        self.status.set("Opened Lily CLI in a separate terminal.")

    def minimize(self) -> None:
        self.root.iconify()

    def quit(self) -> None:
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    LilyDesktop().run()


if __name__ == "__main__":
    main()
