# Lily — Product Roadmap

> Last reset: 2026-07-14. This roadmap tracks evidence that Lily is useful and
> shippable, not the existence of modules or demos.

## Honest current state

Lily is a broad **feature-complete prototype**, not a finished product. The previous
roadmap declared success when code for a feature existed. That produced impressive
breadth—memory, voice, agents, vision, security, and a dashboard—but did not prove
that a new person could install Lily, trust it, or use it every day.

The prototype inventory is preserved in git history. From here on, a checkbox needs
behavioral tests or user evidence, and release checks do not pass merely because the
roadmap has no open work.

## What “we made it” means

Lily reaches beta when all of these are true:

- A new Windows user can install and reach a first useful answer in under 10 minutes.
- The desktop app supports the complete daily loop without requiring a terminal.
- Memory is inspectable, editable, exportable, and recoverable without data loss.
- Core flows have automated tests and every release artifact passes a clean-machine check.
- At least five real users use Lily on three separate days in one week and two return the following week.
- Users can explain one recurring job Lily does better than a normal chat app.

## M0 — Make the prototype real

- [x] Put conversation in the dashboard; the desktop surface can now perform Lily's core job.
- [x] Share one conversation service between CLI and dashboard so memory behavior cannot drift.
- [x] Add behavioral tests for conversation context, persistence, and the dashboard contract.
- [x] Make the release check run behavioral tests instead of treating an empty roadmap as proof.
- [x] Add `lily doctor` with actionable checks for Python, Ollama, models, audio, storage, and ports.
- [ ] Split core and optional dependencies so text chat does not require the full voice/vision stack.
- [ ] Replace repository scripts with a one-command Windows installer and uninstaller.
- [ ] Prove the packaged app on a clean Windows VM and publish the exact compatibility matrix.

Exit evidence: clean-machine install video, release check output, and a first-answer time under 10 minutes.

## M1 — Build one lovable daily loop

- [ ] Make the dashboard the primary app: chat, brief, reminders, projects, and settings in one flow.
- [ ] Stream responses and show tool activity, cancellation, retry, and useful failure recovery.
- [ ] Add an onboarding flow that configures a model and demonstrates one real task.
- [ ] Turn the daily brief into an actionable workspace, not a block of generated text.
- [ ] Let users create, complete, snooze, and edit reminders from the dashboard.
- [ ] Measure local opt-in product signals: first answer, repeated use, failures, and feature adoption.
- [ ] Run five user sessions and choose the single strongest recurring job from evidence.

Exit evidence: five weekly users, three-day activation, two week-two returns, and one clearly repeated job.

## M2 — Earn trust

- [ ] Add a memory inspector with edit, forget, export, import, and provenance for every memory.
- [ ] Add automatic encrypted backups plus a tested restore drill.
- [ ] Show permission prompts and a durable audit trail before sensitive tools run.
- [ ] Threat-model localhost APIs, prompt injection, file access, secrets, and model/tool boundaries.
- [ ] Add schema migrations and rollback tests for every persisted store.
- [ ] Define retention controls and a true “delete everything” verification flow.

Exit evidence: restore succeeds from a corrupted working database and the security checklist has no open P0/P1 issues.

## M3 — Private beta

- [ ] Add crash-safe logs and an explicit, redacted diagnostic bundle.
- [ ] Version the app, database, config, and release artifacts consistently.
- [ ] Add signed Windows builds, checksums, release notes, and rollback instructions.
- [ ] Test upgrade paths from the previous two releases.
- [ ] Publish limitations and resource requirements without hiding optional-model costs.
- [ ] Recruit 20 private-beta users and close every activation-blocking issue.

Exit evidence: 20 installs, 60% first-week activation, no known data-loss bug, and a reproducible signed release.

## Build rules

1. Ship vertical user outcomes before adding another agent or modality.
2. A feature is done only with a user-visible flow, failure handling, and proportional tests.
3. Keep local-first guarantees explicit; cloud use remains opt-in per action.
4. Never use roadmap completion as a release gate.
5. Preserve user data across upgrades or block the upgrade safely.
