# Lily — Mega Roadmap 🌸

> A local-first, open-source personal AI operating-system layer.
> **Every checkbox below = one git push.** Check it, push it, move on.

Codenames:
- **v1 Spark** — Easy Prototype (she's alive: text, memory, persona, basic senses)
- **v2 Voice** — Effort (voice, orchestrator, agents, dashboard, modes)
- **v3 Prime** — Effort Pro (vision, timeline, encrypted memory, cloud-burst, autonomy)

Stack (100% open source, local-first): Ollama · faster-whisper · Piper · openWakeWord ·
SQLite + sqlite-vec · Textual / FastAPI+Svelte · APScheduler · psutil · GitPython · mss · RapidOCR

---

## v1 — Lily Spark (Easy Prototype)

### Bring her alive
- [x] P0  Repo scaffold (README, ROADMAP, LICENSE, .gitignore, package skeleton)
- [x] P1  Brain online — Ollama client, streaming chat
- [x] P2  Persona — Lily's voice/personality system prompt
- [x] P3  Conversation memory (SQLite) — she remembers within a session
- [x] P4  CLI REPL — talk to Lily in the terminal *(← ALIVE)*
- [x] P5  Config system (model, host, paths via env + file)
- [x] P6  Logging + graceful errors (Ollama down, model missing)

### Give her senses & hands
- [x] P7  Tool framework — let Lily call local functions
- [x] P8  System telemetry tool (psutil: CPU/GPU/RAM/battery/temp)
- [x] P9  Notes & reminders tool (SQLite-backed)
- [x] P10 Scheduler (APScheduler) — timed reminders fire
- [x] P11 Long-term memory — facts/preferences she recalls across sessions
- [x] P12 Rich TUI polish (panels, markdown rendering, status line)
- [x] P13 Daily brief command ("Lily, what's up today?")
- [x] P14 `lily` launcher script + first-run setup (model pull check)

---

## v2 — Lily Voice (Effort)

### She speaks & listens
- [x] E0  STT — faster-whisper (speech → text)
- [x] E1  TTS — Piper (Lily's spoken voice)
- [x] E2  Wake word — openWakeWord ("Lily")
- [x] E3  Tier-2 conversation mode (no wake word mid-session)
- [x] E4  Push-to-talk + barge-in (interrupt her mid-sentence)

### Architecture
- [x] E5  Orchestrator agent (routes intent → agents)
- [x] E6  Agent bus (pub/sub, agent registration SDK)
- [x] E7  Planner agent (multi-step task decomposition)
- [x] E8  Memory layers: project memory
- [x] E9  Memory layers: behavior memory (habits, work hours)
- [x] E10 Vector recall (sqlite-vec embeddings + semantic search)

### Modes & interrupts
- [x] E11 Passive / Active mode switching
- [x] E12 Resource manager (load/unload models on mode change)
- [x] E13 Interrupt priority engine (low → emergency)
- [x] E14 Notification batching (defend focus, no spam)

### Real agents (healthy versions)
- [x] E15 Dev agent — watch git/terminal, detect build/test failures, suggest fixes
- [x] E16 Git agent — weekly "what I actually shipped" digest (NOT vanity streaks)
- [x] E17 Calendar agent — local .ics / CalDAV (open source), conflict + prep reminders
- [x] E18 Security watchdog — secret-in-clipboard / repo scan (local only)
- [x] E19 Opportunity agent — RSS/Atom feeds only (CTFTime, conf CFPs), no scraping

### Dashboard
- [x] E20 Dashboard backend (FastAPI, local-only bind)
- [x] E21 Dashboard UI (static HTML/CSS/JS, no build) — system / work / calendar / security cards
- [x] E22 Live updates (websocket) + card framework

---

## v3 — Lily Prime (Effort Pro)

### Eyes
- [x] X0  Screen capture (mss) — opt-in, on-demand
- [x] X1  OCR (RapidOCR) — read text on screen
- [x] X2  Vision model (llava / qwen-vl via Ollama) — understand UI/errors
- [x] X3  Context fusion — combine vision + git + active window into "what am I doing"

### Memory of a life
- [x] X4  Timeline store (append-only, chronological)
- [x] X5  Life replay query ("what was I doing last Thursday?")
- [x] X6  "Why" memory — capture decisions + reasons, not just events
- [x] X7  Instant retrieval ("find that PDF about memory hierarchy")

### Security (Lily guards her own hoard)
- [x] X8  Encrypted memory at rest (SQLCipher / age)
- [x] X9  Per-agent access audit log
- [x] X10 Panic-wipe + local key unlock

### Intelligence & autonomy
- [x] X11 Cloud-burst reasoning — escalate only hard queries to a frontier API
- [ ] X12 Adaptive dashboard engine (cards appear/vanish by usage)
- [ ] X13 Anti-distraction agent (negotiates, protects focus blocks)
- [ ] X14 Feedback agent (👍/👎 → real preference model, not a counter)
- [ ] X15 Multi-agent coordination (agents collaborate on a goal)
- [ ] X16 Predictive assistance (anticipate next step from patterns)
- [ ] X17 Sleep/Wake full state preservation across reboots

---

### Rules of the build
1. One checkbox = one focused commit + push.
2. Every push leaves Lily *runnable* — never commit her broken.
3. Local-first always. Cloud is opt-in and explicit (X11 only).
4. Healthy incentives: no vanity-metric gaming, no scraping that breaks ToS.
