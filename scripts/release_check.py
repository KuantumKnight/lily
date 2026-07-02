"""Release readiness checks for Lily."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import smoke_check


def main() -> int:
    ok = smoke_check.main() == 0
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    unchecked = [line for line in roadmap.splitlines() if "- [ ]" in line]
    if unchecked:
        print("FAIL roadmap has unchecked items:")
        for line in unchecked:
            print(line)
        ok = False
    else:
        print("ok roadmap complete")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
