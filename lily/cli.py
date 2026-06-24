"""The terminal REPL — talk to Lily. This is where she comes alive."""

from rich.console import Console

from . import brain, engine, memory, tools
from .config import CONTEXT_WINDOW, MODEL
from .log import get_logger
from .persona import PERSONA

console = Console()
log = get_logger("cli")

EXIT_WORDS = {"exit", "quit", "bye", "sleep"}


def _build_context(user_input: str) -> list[dict]:
    memory.remember("user", user_input)
    return [{"role": "system", "content": PERSONA}, *memory.recent(CONTEXT_WINDOW)]


def main() -> None:
    tools.load_builtins()
    log.info("Lily session started (model=%s)", MODEL)
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

        try:
            with console.status("[magenta]Lily is thinking…[/]", spinner="dots"):
                reply = engine.converse(messages)
        except brain.BrainOffline as exc:
            console.print(f"[bold red]✗ Lily's brain is offline:[/] {exc}")
            continue

        console.print(f"[bold magenta]lily ›[/] {reply}")
        memory.remember("assistant", reply)

    log.info("Lily session ended")
    console.print("\n[dim]Lily: resting. 🌙[/]")


if __name__ == "__main__":
    main()
