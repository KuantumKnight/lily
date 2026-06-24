"""The terminal REPL — talk to Lily. This is where she comes alive."""

from rich.console import Console

from . import brain, memory
from .config import CONTEXT_WINDOW, MODEL
from .persona import PERSONA

console = Console()

EXIT_WORDS = {"exit", "quit", "bye", "sleep"}


def _build_context(user_input: str) -> list[dict]:
    memory.remember("user", user_input)
    return [{"role": "system", "content": PERSONA}, *memory.recent(CONTEXT_WINDOW)]


def main() -> None:
    console.print(
        f"[bold magenta]Lily[/] is awake. "
        f"[dim](brain: {MODEL} · type 'exit' to sleep)[/]\n"
    )
    while True:
        try:
            user_input = console.input("[bold cyan]you ›[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input.lower() in EXIT_WORDS:
            break

        messages = _build_context(user_input)

        console.print("[bold magenta]lily ›[/] ", end="")
        reply = ""
        try:
            for token in brain.stream_chat(messages):
                console.print(token, end="")
                reply += token
        except brain.BrainOffline as exc:
            console.print(f"\n[bold red]✗ Lily's brain is offline:[/] {exc}")
            continue

        console.print()
        memory.remember("assistant", reply)

    console.print("\n[dim]Lily: resting. 🌙[/]")


if __name__ == "__main__":
    main()
