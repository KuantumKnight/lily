"""The terminal REPL — talk to Lily. This is where she comes alive."""

import shlex

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from . import brain, brief, engine, first_run, memory, scheduler, stt, tools, tts, wake
from .config import CONTEXT_WINDOW, MODEL, TTS_AUTOSPEAK
from .log import get_logger
from .persona import PERSONA

console = Console()
log = get_logger("cli")

EXIT_WORDS = {"exit", "quit", "bye", "sleep"}
BRIEF_WORDS = {"brief", "daily brief", "what's up today", "whats up today"}
TRANSCRIBE_PREFIX = "transcribe "
SAY_PREFIX = "say "

_autospeak = TTS_AUTOSPEAK


def _speak(text: str) -> None:
    """Voice ``text`` aloud, surfacing setup problems without crashing the REPL."""
    try:
        tts.speak(text)
    except tts.TTSUnavailable as exc:
        console.print(f"[yellow]voice ›[/] {exc}")


def _build_context(user_input: str) -> list[dict]:
    memory.remember("user", user_input)
    system_prompt = PERSONA
    facts = memory.long_term_context()
    if facts:
        system_prompt = f"{system_prompt}\n\n{facts}"
    return [{"role": "system", "content": system_prompt}, *memory.recent(CONTEXT_WINDOW)]


def _print_reminder(row) -> None:
    due = f" [dim]({row['due_at']})[/]" if row["due_at"] else ""
    console.print(f"\n[bold yellow]reminder ›[/] {row['content']}{due}")


def _print_reply(reply: str) -> None:
    console.print(Panel(Markdown(reply or "..."), title="Lily", border_style="magenta"))


def _transcribe_command(user_input: str) -> bool:
    if not user_input.lower().startswith(TRANSCRIBE_PREFIX):
        return False

    try:
        parts = shlex.split(user_input, posix=False)
    except ValueError as exc:
        console.print(f"[bold red]transcribe ›[/] {exc}")
        return True

    if len(parts) < 2:
        console.print("[bold red]transcribe ›[/] usage: transcribe path\\to\\audio.wav")
        return True

    audio_path = " ".join(parts[1:]).strip('"')
    with console.status("[magenta]Lily is listening…[/]", spinner="dots"):
        try:
            transcript = stt.transcribe_file(audio_path)
        except stt.STTUnavailable as exc:
            console.print(f"[bold red]transcribe ›[/] {exc}")
            return True

    _print_reply(transcript)
    memory.remember("user", f"[transcribed audio] {transcript}")
    return True


def _say_command(user_input: str) -> bool:
    if not user_input.lower().startswith(SAY_PREFIX):
        return False
    text = user_input[len(SAY_PREFIX):].strip()
    if text:
        with console.status("[magenta]Lily is speaking…[/]", spinner="dots"):
            _speak(text)
    return True


def _listen_command(user_input: str) -> bool:
    if user_input.lower() != "listen":
        return False

    def _on_wake(name: str, score: float) -> bool:
        console.print(f"\n[bold magenta]Lily ›[/] heard her wake word [dim]({name} {score:.2f})[/]")
        if _autospeak:
            _speak("Yes?")
        return False  # keep listening

    console.print("[dim]listening for wake word… press Ctrl+C to stop[/]")
    try:
        wake.listen_for_wake(_on_wake)
    except wake.WakeUnavailable as exc:
        console.print(f"[bold red]listen ›[/] {exc}")
    except KeyboardInterrupt:
        console.print("[dim]stopped listening[/]")
    return True


def _voice_command(user_input: str) -> bool:
    global _autospeak
    if user_input.lower() not in {"voice", "voice on", "voice off"}:
        return False
    if user_input.lower() == "voice on":
        _autospeak = True
    elif user_input.lower() == "voice off":
        _autospeak = False
    else:
        _autospeak = not _autospeak
    console.print(f"[dim]voice › auto-speak {'on' if _autospeak else 'off'}[/]")
    return True


def main() -> None:
    tools.load_builtins()
    setup_warnings = first_run.check_runtime()
    reminder_scheduler = scheduler.start_reminder_scheduler(_print_reminder)
    log.info("Lily session started (model=%s)", MODEL)
    console.print(Panel.fit("[bold magenta]Lily[/] is awake", border_style="magenta"))
    console.print(
        f"[dim]brain: {MODEL} | tools: {len(tools.schemas() or [])} | "
        "type 'exit' to sleep | brief | transcribe <audio> | say <text> | listen | voice[/]\n"
    )
    for warning in setup_warnings:
        console.print(f"[yellow]setup ›[/] {warning}")
    if setup_warnings:
        console.print()
    try:
        while True:
            try:
                user_input = console.input("[bold cyan]you ›[/] ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not user_input:
                continue
            if user_input.lower() in EXIT_WORDS:
                break
            if user_input.lower() in BRIEF_WORDS:
                _print_reply(brief.daily_brief())
                continue
            if _transcribe_command(user_input):
                continue
            if _say_command(user_input):
                continue
            if _listen_command(user_input):
                continue
            if _voice_command(user_input):
                continue

            messages = _build_context(user_input)

            try:
                with console.status("[magenta]Lily is thinking…[/]", spinner="dots"):
                    reply = engine.converse(messages)
            except brain.BrainOffline as exc:
                console.print(f"[bold red]✗ Lily's brain is offline:[/] {exc}")
                continue

            _print_reply(reply)
            memory.remember("assistant", reply)
            if _autospeak and reply:
                _speak(reply)
    finally:
        if reminder_scheduler is not None:
            reminder_scheduler.shutdown(wait=False)
            log.info("reminder scheduler stopped")

    log.info("Lily session ended")
    console.print("\n[dim]Lily: resting. 🌙[/]")


if __name__ == "__main__":
    main()
