"""The conversation engine — runs the think → call tools → think loop.

Lily proposes tool calls, we execute them locally, feed the results back, and repeat
until she has a final answer (or we hit the round limit). This is the heart of how
every agent's capabilities reach the conversation.
"""

from . import brain, tools
from .log import get_logger

log = get_logger("engine")

MAX_TOOL_ROUNDS = 5


def _normalise_tool_calls(raw) -> list[dict]:
    """Convert the model's tool_calls into plain dicts we can replay back to it."""
    out = []
    for call in raw:
        name, args = _tool_call_name_args(call)
        out.append(
            {
                "function": {
                    "name": name,
                    "arguments": args,
                }
            }
        )
    return out


def _tool_call_name_args(call) -> tuple[str, dict]:
    """Support both object-style and dict-style Ollama tool calls."""
    if isinstance(call, dict):
        fn = call.get("function") or {}
        return str(fn.get("name") or ""), dict(fn.get("arguments") or {})
    return str(call.function.name), dict(call.function.arguments or {})


def converse(messages: list[dict]) -> str:
    """Drive a full turn (mutates `messages` with tool traffic). Returns Lily's reply text."""
    tool_schemas = tools.schemas()

    for _ in range(MAX_TOOL_ROUNDS):
        msg = brain.chat_once(messages, tools=tool_schemas)
        tool_calls = msg.get("tool_calls")

        if not tool_calls:
            return (msg.get("content") or "").strip()

        # Record Lily's tool-call turn, then run each tool and feed results back.
        messages.append(
            {
                "role": "assistant",
                "content": msg.get("content") or "",
                "tool_calls": _normalise_tool_calls(tool_calls),
            }
        )
        for call in tool_calls:
            name, args = _tool_call_name_args(call)
            result = tools.execute(name, args)
            log.info("tool %s(%s) -> %s", name, args, result[:200])
            messages.append({"role": "tool", "name": name, "content": result})

    # Out of rounds — get a final answer without offering more tools.
    final = brain.chat_once(messages)
    return (final.get("content") or "").strip()
