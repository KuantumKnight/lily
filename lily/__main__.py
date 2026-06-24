"""Entry point:  python -m lily"""

import sys

# Windows terminals often default to cp1252, which can't encode Lily's emoji/glyphs.
# Force UTF-8 on stdio before anything prints.
for _stream in (sys.stdout, sys.stdin, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

from .cli import main

if __name__ == "__main__":
    main()
