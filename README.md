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
```

```
Lily is awake. Type 'exit' to sleep.

you › hey Lily, who are you?
lily › ...
```

Lily runs first-start checks for installed Python packages, Ollama reachability, and
whether the configured model is pulled. Inside the REPL, type `brief` for a local daily
brief with system status, reminders, notes, and remembered facts.

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

Every request flows through an **orchestrator** that routes it to the right
agent (type `agents` to see the roster). Anything not claimed by a specialized
agent falls through to the default conversation agent, so behavior is unchanged
until you add more. Register your own with the `lily.agents` SDK.

## Configuration

Environment variables (all optional):

| Var | Default | Meaning |
|---|---|---|
| `LILY_MODEL` | `qwen3:8b` | Ollama model used as Lily's brain |
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

## Philosophy

- **Local-first.** Your life doesn't leave your machine unless you say so.
- **Open source only.** No proprietary lock-in anywhere in the stack.
- **Healthy by design.** No vanity-metric gaming, no ToS-breaking scraping.
- **Always runnable.** Every commit leaves Lily working.

## License

MIT — see [LICENSE](./LICENSE).
