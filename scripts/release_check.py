"""Release readiness checks for Lily."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import smoke_check


def main() -> int:
    ok = smoke_check.main() == 0
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if result.wasSuccessful():
        print(f"ok behavioral tests ({result.testsRun})")
    else:
        print("FAIL behavioral tests")
        ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
