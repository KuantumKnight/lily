# Lily 🌸

A local-first, open-source **personal AI operating-system layer** — a chief-of-staff that
lives on your machine, runs on open models, and keeps your data yours.

Lily is built in three escalating versions:

| Version | Codename | State |
|---|---|---|
| v1 | **Spark** | Alive: talks, remembers, basic senses (text-only, 100% local) |
| v2 | **Voice** | Voice I/O, agent orchestrator, dashboard, passive/active modes |
| v3 | **Prime** | Vision, life-timeline, encrypted memory, cloud-burst, autonomy |

See **[ROADMAP.md](./ROADMAP.md)** for the full build ticklist (each checkbox = one git push).

## Quick start (v1 Spark)

Requires [Ollama](https://ollama.com) running locally with a model pulled.

```bash
# 1. pull a brain (once)
ollama pull qwen3:8b

# 2. install deps
python -m venv .venv
. .venv/Scripts/activate        # Windows:  .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. wake her up
python -m lily

# Windows shortcut after setup
.\lily.ps1

# Windows desktop app
.\lily-app.ps1
```

```
Lily is awake. Type 'exit' to sleep.

you › hey Lily, who are you?
lily › ...
```

Lily runs first-start checks for installed Python packages, Ollama reachability, and
whether the configured model is pulled. Inside the REPL, type `brief` for a local daily
brief with system status, reminders, notes, and remembered facts.

The Windows desktop app opens a small Lily control window. It can start/open the local
dashboard, launch the CLI in a separate terminal, and minimizes normally to the Windows
taskbar. Closing the app window minimizes it; use **Quit** to exit the desktop shell.

To build a standalone Windows executable:

```powershell
.\build-windows-app.ps1
```

The output is written to `dist\Lily\Lily.exe`.

For local speech-to-text, install the requirements and run:

```bash
transcribe path/to/audio.wav
```

The first transcription loads the configured faster-whisper model locally.

For Lily's spoken voice, download a Piper voice (`.onnx` + `.onnx.json`) from
[rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices), point `tts_voice`
at the `.onnx` file, then use:

```text
say hello, I'm Lily
voice on       # auto-speak Lily's replies; 'voice off' to stop
```

To have Lily listen for her wake word, type `listen` in the REPL (Ctrl+C to stop).
openWakeWord ships no "Lily" model yet, so `wake_model` defaults to the bundled
`hey_jarvis`; train a custom model and point `wake_model` at its `.onnx`/`.tflite`
to wake her by name.

For full hands-free conversation, type `chat`: say your wake word, then talk —
Lily transcribes, replies, and speaks back. She keeps the conversation going
without re-waking until you fall silent (back to sleep) or say "bye"/"exit".
Tune `mic_silence_threshold` if she cuts you off or never stops listening.

While she's speaking, press any key to **barge in** — she stops mid-sentence so
you can talk over her. Set `push_to_talk = true` to gate each turn behind a
keypress instead of voice-activated recording.

For opt-in screen capture, type `screenshot` or `capture screen` in the REPL.
Lily writes a PNG under `data/screenshots` by default. She never captures the
screen in the background; capture is on-demand only. Use `screenshot 0` to grab
the virtual monitor spanning all displays.

To read text from the screen, type `ocr`, `read screen`, or `screen text`.
Lily uses RapidOCR locally and only after you explicitly ask. You can also pass
an image path to OCR an existing screenshot.

For local visual understanding, pull a vision model such as `llava:7b`, then
type `look`, `vision`, or `inspect screen`. Lily sends the explicitly requested
capture or image path to Ollama on your machine, not to a cloud API.

For a fused "what am I doing?" snapshot, type `context` or `what am I doing`.
Lily combines the active window title, git status, screen OCR, and local vision
summary on demand.

Lily also maintains an append-only timeline in SQLite. Normal user/Lily turns
are recorded chronologically, and tools can append or search timeline events.
Ask `what was I doing last Thursday?`, `replay yesterday`, or `replay 2026-06-30`
to query that history.

Decision memory stores the "why" behind choices separately from raw events. Use
the `remember_decision` tool to save a decision, reason, and optional context.

Instant retrieval can find local files and PDFs by name or text. Try `find memory
hierarchy PDF`; PDF content search uses `pypdf` when available.

For encrypted memory backups, install `age`, set `LILY_AGE_RECIPIENT`, then use
the `encrypt_memory` tool. Set `LILY_AGE_IDENTITY` to decrypt a saved `.age`
database back to the local SQLite memory file.

Every agent turn is recorded in a local audit table with agent, action, resource,
and detail. Use `recent_audit` to inspect access history.

Every request flows through an **orchestrator** that routes it to the right
agent (type `agents` to see the roster). Anything not claimed by a specialized
agent falls through to the default conversation agent, so behavior is unchanged
until you add more. Agents communicate over an in-process **event bus**
(`user.message`, `lily.reply`, `reminder.fired`, …). Build your own agent with
the `lily.sdk` SDK — `register` a handler and `subscribe` to bus topics.

Lily keeps **project memory**: set an active project and she scopes notes to it
and folds them into her context. Just ask her ("we're working on the taxes
project", "note that the receipts are in Drive", "what do you have on this
project?") and she'll use the project tools.

She also builds **behavior memory** from when you interact — over time she learns
your typical active hours and busiest day ("what are my work hours?"). It stays
quiet until there's enough data to be more than a guess.

For **semantic recall**, Lily embeds facts and project notes (local embedding
model via Ollama) and searches them by meaning — "find what I noted about the
budget" works even without the exact words. Pull the embedding model once
(`ollama pull nomic-embed-text`), then ask her to reindex and recall. Vectors are
stored as BLOBs in the same local SQLite DB; no data leaves the machine.

## Configuration

Environment variables (all optional):

| Var | Default | Meaning |
|---|---|---|
| `LILY_MODEL` | `qwen3:8b` | Ollama model used as Lily's brain |
| `LILY_EMBED_MODEL` | `nomic-embed-text` | Ollama model used for semantic recall |
| `LILY_VISION_MODEL` | `llava:7b` | Ollama vision model used for local image understanding |
| `LILY_OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `LILY_STT_MODEL` | `base` | faster-whisper model for speech-to-text |
| `LILY_STT_DEVICE` | `cpu` | faster-whisper device, usually `cpu` or `cuda` |
| `LILY_STT_COMPUTE_TYPE` | `int8` | faster-whisper compute type |
| `LILY_TTS_VOICE` | _(unset)_ | path to a Piper `.onnx` voice model |
| `LILY_TTS_AUTOSPEAK` | `false` | speak Lily's replies aloud by default |
| `LILY_WAKE_MODEL` | `hey_jarvis` | openWakeWord model name or `.onnx`/`.tflite` path |
| `LILY_WAKE_THRESHOLD` | `0.5` | wake-word detection confidence (0–1) |
| `LILY_BARGE_IN` | `true` | let a keypress interrupt Lily mid-sentence |
| `LILY_PUSH_TO_TALK` | `false` | gate each voice turn behind a keypress |
| `LILY_SCREENSHOT_DIR` | `data/screenshots` | where explicit screen captures are saved |
| `LILY_ENCRYPTED_DB_PATH` | `data/lily.db.age` | encrypted SQLite memory backup path |
| `LILY_AGE_RECIPIENT` | _(unset)_ | age public recipient used to encrypt memory |
| `LILY_AGE_IDENTITY` | _(unset)_ | age identity file used to decrypt memory |

## Philosophy

- **Local-first.** Your life doesn't leave your machine unless you say so.
- **Open source only.** No proprietary lock-in anywhere in the stack.
- **Healthy by design.** No vanity-metric gaming, no ToS-breaking scraping.
- **Always runnable.** Every commit leaves Lily working.

## License

MIT — see [LICENSE](./LICENSE).
