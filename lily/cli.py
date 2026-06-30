"""The terminal REPL — talk to Lily. This is where she comes alive."""

import shlex
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

import time

from . import (
    agents,
    brain,
    brief,
    bus,
    context,
    first_run,
    interrupt,
    memory,
    mic,
    mode as mode_module,
    notifications,
    ocr,
    orchestrator,
    resource_manager,
    scheduler,
    screen,
    stt,
    tools,
    tts,
    vision,
    wake,
)
from .config import BARGE_IN, CONTEXT_WINDOW, DASHBOARD_ENABLE, MODEL, PUSH_TO_TALK, TTS_AUTOSPEAK
from .log import get_logger
from .persona import PERSONA

console = Console()
log = get_logger("cli")

EXIT_WORDS = {"exit", "quit", "bye", "sleep"}
BRIEF_WORDS = {"brief", "daily brief", "what's up today", "whats up today"}
TRANSCRIBE_PREFIX = "transcribe "
SAY_PREFIX = "say "
SCREENSHOT_WORDS = {"screenshot", "screen capture", "capture screen"}
OCR_WORDS = {"ocr", "read screen", "screen text"}
VISION_WORDS = {"look", "vision", "inspect screen"}
CONTEXT_WORDS = {"context", "what am i doing", "what am i working on"}

_autospeak = TTS_AUTOSPEAK


def _speak(text: str) -> None:
    """Voice ``text`` aloud, surfacing setup problems without crashing the REPL."""
    try:
        tts.speak(text)
    except tts.TTSUnavailable as exc:
        console.print(f"[yellow]voice ›[/] {exc}")


def _build_context(user_input: str) -> list[dict]:
    memory.remember("user", user_input)
    memory.record_activity("message")
    system_prompt = PERSONA
    facts = memory.long_term_context()
    if facts:
        system_prompt = f"{system_prompt}\n\n{facts}"
    project = memory.project_context()
    if project:
        system_prompt = f"{system_prompt}\n\n{project}"
    habits = memory.behavior_summary()
    if habits:
        system_prompt = f"{system_prompt}\n\n{habits}"
    return [{"role": "system", "content": system_prompt}, *memory.recent(CONTEXT_WINDOW)]


def _print_reminder(row) -> None:
    due = f" [dim]({row['due_at']})[/]" if row["due_at"] else ""
    console.print(f"\n[bold yellow]reminder ›[/] {row['content']}{due}")
    bus.publish("reminder.fired", {"content": row["content"], "due_at": row["due_at"]})


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


def _screenshot_command(user_input: str) -> bool:
    lowered = user_input.lower().strip()
    if not any(
        lowered == word or lowered.startswith(f"{word} ")
        for word in SCREENSHOT_WORDS
    ):
        return False

    monitor = 1
    try:
        parts = shlex.split(user_input, posix=False)
    except ValueError as exc:
        console.print(f"[bold red]screenshot ›[/] {exc}")
        return True
    if len(parts) > 1 and parts[-1].isdigit():
        monitor = int(parts[-1])

    with console.status("[magenta]capturing screen…[/]", spinner="dots"):
        try:
            path = screen.capture_screen(monitor=monitor)
        except screen.ScreenCaptureUnavailable as exc:
            console.print(f"[bold red]screenshot ›[/] {exc}")
            return True
    console.print(f"[dim]screenshot › {path}[/]")
    memory.remember("user", f"[screen captured] {path}")
    return True


def _ocr_command(user_input: str) -> bool:
    lowered = user_input.lower().strip()
    if not any(lowered == word or lowered.startswith(f"{word} ") for word in OCR_WORDS):
        return False

    image_path = ""
    monitor = 1
    try:
        parts = shlex.split(user_input, posix=False)
    except ValueError as exc:
        console.print(f"[bold red]ocr ›[/] {exc}")
        return True
    if len(parts) > 1:
        tail = parts[-1].strip('"')
        if tail.isdigit():
            monitor = int(tail)
        elif Path(tail).exists():
            image_path = tail

    with console.status("[magenta]reading screen text…[/]", spinner="dots"):
        try:
            text = ocr.read_text(image_path=image_path, monitor=monitor)
        except ocr.OCRUnavailable as exc:
            console.print(f"[bold red]ocr ›[/] {exc}")
            return True
    _print_reply(text or "No readable text found.")
    memory.remember("user", f"[screen OCR] {text}")
    return True


def _vision_command(user_input: str) -> bool:
    lowered = user_input.lower().strip()
    if not any(
        lowered == word or lowered.startswith(f"{word} ")
        for word in VISION_WORDS
    ):
        return False

    prompt = "Describe what is visible. Focus on UI state, errors, and actionable details."
    image_path = ""
    monitor = 1
    try:
        parts = shlex.split(user_input, posix=False)
    except ValueError as exc:
        console.print(f"[bold red]vision ›[/] {exc}")
        return True
    if len(parts) > 1:
        tail = parts[-1].strip('"')
        if tail.isdigit():
            monitor = int(tail)
            prompt = " ".join(parts[1:-1]).strip() or prompt
        elif Path(tail).exists():
            image_path = tail
            prompt = " ".join(parts[1:-1]).strip() or prompt
        else:
            prompt = " ".join(parts[1:]).strip() or prompt

    with console.status("[magenta]looking locally…[/]", spinner="dots"):
        try:
            description = vision.describe_image(
                prompt=prompt,
                image_path=image_path,
                monitor=monitor,
            )
        except vision.VisionUnavailable as exc:
            console.print(f"[bold red]vision ›[/] {exc}")
            return True
    _print_reply(description or "No visual description returned.")
    memory.remember("user", f"[screen vision] {description}")
    return True


def _context_command(user_input: str) -> bool:
    lowered = user_input.lower().strip(" ?")
    if lowered not in CONTEXT_WORDS:
        return False
    with console.status("[magenta]fusing local context…[/]", spinner="dots"):
        summary = context.snapshot(include_vision=True)
    _print_reply(summary)
    memory.remember("user", f"[context snapshot] {summary}")
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


def _speak_interruptible(text: str) -> bool:
    """Speak ``text`` aloud but let the user barge in with a keypress.

    Returns True if interrupted. Falls back to blocking speech if barge-in is off.
    """
    if not BARGE_IN:
        _speak(text)
        return False
    try:
        duration = tts.speak_async(text)
    except tts.TTSUnavailable as exc:
        console.print(f"[yellow]voice ›[/] {exc}")
        return False
    if duration <= 0:
        return False

    interrupt.drain()
    deadline = time.monotonic() + duration + 0.2
    while time.monotonic() < deadline:
        if interrupt.key_pressed():
            tts.stop()
            console.print("[dim](interrupted — go ahead)[/]")
            return True
        time.sleep(0.05)
    return False


def _voice_reply(text: str) -> None:
    """One spoken turn: build context, think, print, and speak the reply (interruptible)."""
    messages = _build_context(text)
    try:
        with console.status("[magenta]Lily is thinking…[/]", spinner="dots"):
            reply = orchestrator.handle(text, messages)
    except brain.BrainOffline as exc:
        console.print(f"[bold red]✗ Lily's brain is offline:[/] {exc}")
        return
    _print_reply(reply)
    memory.remember("assistant", reply)
    _speak_interruptible(reply)


def _active_conversation() -> bool:
    """Tier-2 mode: converse without re-waking. Return True to leave voice chat entirely."""
    console.print("[bold magenta]Lily ›[/] I'm listening.")
    if BARGE_IN:
        console.print("[dim](press any key while she's talking to interrupt)[/]")
    mode_module.set_mode(mode_module.MODE_ACTIVE, reason="wake")
    _speak_interruptible("I'm listening.")
    while True:
        if PUSH_TO_TALK:
            console.print("[dim](push-to-talk) press any key to speak…[/]")
            interrupt.wait_key()
        with console.status("[magenta]listening…[/]", spinner="dots"):
            samples = mic.record_until_silence()
        text = stt.transcribe_array(samples).strip()
        if not text:
            console.print("[dim]…silence — back to sleep. Say the wake word again.[/]")
            mode_module.set_mode(mode_module.MODE_PASSIVE, reason="silence")
            return False
        console.print(f"[bold cyan]you (voice) ›[/] {text}")
        if text.lower().strip(" .,!?") in EXIT_WORDS:
            mode_module.set_mode(mode_module.MODE_PASSIVE, reason="exit")
            return True
        _voice_reply(text)


def _chat_command(user_input: str) -> bool:
    if user_input.lower() not in {"chat", "converse"}:
        return False

    woke = {"hit": False}

    def _on_wake(name: str, score: float) -> bool:
        woke["hit"] = True
        return True  # stop the wake listener and go active

    try:
        while True:
            woke["hit"] = False
            console.print("[dim]listening for wake word… (Ctrl+C to leave voice chat)[/]")
            wake.listen_for_wake(_on_wake)
            if not woke["hit"]:
                break
            if _active_conversation():
                break
    except (wake.WakeUnavailable, mic.MicUnavailable, stt.STTUnavailable) as exc:
        console.print(f"[bold red]chat ›[/] {exc}")
    except KeyboardInterrupt:
        pass
    console.print("[dim]left voice chat[/]")
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


def _mode_command(user_input: str) -> bool:
    lowered = user_input.lower().strip()
    if lowered not in {"mode", "mode?", "mode passive", "mode active"}:
        return False
    if lowered in {"mode passive", "mode active"}:
        target = lowered.split()[1]
        mode_module.set_mode(target, reason="cli")
    console.print(f"[dim]mode › {mode_module.current()}[/]")
    return True


def _print_surfaced(topic: str, payload: object) -> None:
    """Render a flushed/urgent notification batch arriving on the bus."""
    if not isinstance(payload, dict):
        return
    for note in payload.get("notifications", []):
        src = f" [dim]({note['source']})[/]" if note.get("source") else ""
        console.print(f"\n[bold yellow]notify ›[/] [{note['priority']}] {note['content']}{src}")


def _notifications_command(user_input: str) -> bool:
    lowered = user_input.lower().strip()
    if lowered not in {"notifications", "pending", "notifications flush"}:
        return False
    if lowered == "notifications flush":
        if not notifications.flush(reason="cli"):
            console.print("[dim]notify › nothing to flush[/]")
        return True
    items = notifications.pending()
    if not items:
        console.print("[dim]notify › no pending notifications[/]")
        return True
    lines = [
        f"[{n.priority}] {n.content}" + (f" [dim]({n.source})[/]" if n.source else "")
        for n in items
    ]
    console.print(Panel("\n".join(lines), title="pending notifications", border_style="yellow"))
    return True


_dashboard_thread = None


def _dashboard_command(user_input: str) -> bool:
    global _dashboard_thread
    if user_input.lower().strip() != "dashboard":
        return False
    from . import dashboard
    from .config import DASHBOARD_HOST, DASHBOARD_PORT

    if _dashboard_thread is not None and _dashboard_thread.is_alive():
        console.print(f"[dim]dashboard › already running at http://{DASHBOARD_HOST}:{DASHBOARD_PORT}[/]")
        return True
    try:
        _dashboard_thread = dashboard.start_in_thread()
    except dashboard.DashboardUnavailable as exc:
        console.print(f"[bold red]dashboard ›[/] {exc}")
        return True
    console.print(f"[dim]dashboard › serving at http://{DASHBOARD_HOST}:{DASHBOARD_PORT}[/]")
    return True


def _agents_command(user_input: str) -> bool:
    if user_input.lower() != "agents":
        return False
    lines = [
        f"[bold]{a.name}[/] — {a.description}"
        + (f" [dim](triggers: {', '.join(a.triggers)})[/]" if a.triggers else "")
        for a in agents.all_agents()
    ]
    console.print(Panel("\n".join(lines) or "none", title="agents", border_style="magenta"))
    return True


def main() -> None:
    tools.load_builtins()
    agents.load_builtins()
    resource_manager.init()
    notifications.init()
    bus.subscribe("notification.surfaced", _print_surfaced)
    if DASHBOARD_ENABLE:
        _dashboard_command("dashboard")
    setup_warnings = first_run.check_runtime()
    reminder_scheduler = scheduler.start_reminder_scheduler(_print_reminder)
    log.info("Lily session started (model=%s)", MODEL)
    console.print(Panel.fit("[bold magenta]Lily[/] is awake", border_style="magenta"))
    console.print(
        f"[dim]brain: {MODEL} | tools: {len(tools.schemas() or [])} | "
        f"agents: {len(agents.all_agents())} | mode: {mode_module.current()} | "
        "exit | brief | listen | chat | voice | mode | notifications | dashboard | agents[/]\n"
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
            if _screenshot_command(user_input):
                continue
            if _ocr_command(user_input):
                continue
            if _vision_command(user_input):
                continue
            if _context_command(user_input):
                continue
            if _listen_command(user_input):
                continue
            if _chat_command(user_input):
                continue
            if _voice_command(user_input):
                continue
            if _mode_command(user_input):
                continue
            if _notifications_command(user_input):
                continue
            if _dashboard_command(user_input):
                continue
            if _agents_command(user_input):
                continue

            messages = _build_context(user_input)

            try:
                with console.status("[magenta]Lily is thinking…[/]", spinner="dots"):
                    reply = orchestrator.handle(user_input, messages)
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
