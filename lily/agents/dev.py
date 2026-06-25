"""The dev agent — runs the test suite and, on failure, asks the brain for a fix.

Routed to on "run tests", "fix", "debug", "build failed". It executes the suite via
:mod:`lily.devtools` (safe, timed subprocess), and if the output trips the failure
detector it feeds the tail of that output to the brain for a concrete suggestion. The
run is announced on the bus as ``dev.tests`` so other agents can react.
"""

from .. import brain, bus
from ..devtools import detect_failure, run_tests
from ..log import get_logger
from . import Agent, register

log = get_logger("dev")

FIX_SYSTEM = (
    "You are Lily's debugging assistant. Given failing build/test output, identify the "
    "most likely root cause and suggest a concrete fix in 2-4 sentences. Be specific; "
    "reference the file or symbol if it appears in the output. No preamble."
)

# Keep brain prompts bounded — the tail usually holds the actual error.
_MAX_OUTPUT_CHARS = 4000


def suggest_fix(output: str) -> str:
    """Ask the brain for a fix given failing output. Raises BrainOffline on failure."""
    tail = output[-_MAX_OUTPUT_CHARS:]
    msg = brain.chat_once(
        [
            {"role": "system", "content": FIX_SYSTEM},
            {"role": "user", "content": f"Build/test output:\n\n{tail}"},
        ]
    )
    return (msg.get("content") or "").strip()


def _handle(query: str, messages: list) -> str:
    rc, output = run_tests()
    failed = rc != 0 or detect_failure(output)
    bus.publish("dev.tests", {"returncode": rc, "failed": failed})
    log.info("tests rc=%s failed=%s", rc, failed)

    if not failed:
        return f"Tests passed. ✅\n\n{output[-1000:]}" if output else "Tests passed. ✅"

    suggestion = ""
    try:
        suggestion = suggest_fix(output)
    except brain.BrainOffline as exc:
        suggestion = f"(brain offline — can't suggest a fix: {exc})"

    tail = output[-1500:]
    return f"Tests failed (exit {rc}).\n\n{tail}\n\n[bold]Suggested fix:[/] {suggestion}"


register(
    Agent(
        name="dev",
        description="Runs the test suite and suggests fixes when the build is broken.",
        handler=_handle,
        triggers=("run tests", "run the tests", "build failed", "tests fail", "debug ", "fix the"),
    )
)
