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

## Configuration

Environment variables (all optional):

| Var | Default | Meaning |
|---|---|---|
| `LILY_MODEL` | `qwen3:8b` | Ollama model used as Lily's brain |
| `LILY_OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |

## Philosophy

- **Local-first.** Your life doesn't leave your machine unless you say so.
- **Open source only.** No proprietary lock-in anywhere in the stack.
- **Healthy by design.** No vanity-metric gaming, no ToS-breaking scraping.
- **Always runnable.** Every commit leaves Lily working.

## License

MIT — see [LICENSE](./LICENSE).
