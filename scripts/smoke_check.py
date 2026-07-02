"""Quick local smoke checks for Lily.

This intentionally avoids network calls, model calls, screen capture, and destructive
operations. It is meant to catch import/registration breakage after feature work.
"""

from __future__ import annotations

import compileall
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    ok = True
    ok = compileall.compile_dir(str(ROOT / "lily"), quiet=1) and ok

    from lily import agents, health, session_state, tools
    from lily.engine import _normalise_tool_calls

    tools.load_builtins()
    agents.load_builtins()

    checks = {
        "tools": len(tools.schemas() or []) > 0,
        "agents": len(agents.all_agents()) > 0,
        "tool_call_dicts": _normalise_tool_calls(
            [{"function": {"name": "get_datetime", "arguments": {}}}]
        )[0]["function"]["name"] == "get_datetime",
        "health_report": health.report().startswith("Runtime health:"),
        "wake_state": isinstance(session_state.restore_summary(), str),
    }

    for name, passed in checks.items():
        print(f"{'ok' if passed else 'FAIL'} {name}")
        ok = bool(passed) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
