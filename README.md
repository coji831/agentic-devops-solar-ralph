# SOLAR-Ralph

[![Copilot 2026 Ready](https://img.shields.io/badge/Copilot-2026_Ready-blue.svg)](https://github.com/features/copilot)
[![Framework SOLAR-Ralph](https://img.shields.io/badge/Framework-SOLAR--Ralph-orange.svg)](#the-solar-framework)
[![License MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Agentic AI should finish tasks autonomously. Most of the time, it doesn't.**

Agents declare success too early. They start work with missing context and fail mid-way. They implement in the wrong direction for hours before you notice. They self-certify their own output. They lose all state when the session ends. And changing one agent breaks everything else.

SOLAR-Ralph is a **harness around your agents**: deterministic control
(LangGraph runtime, `solar-governor/`) + your own specialists as workers. It
keeps the agentic system intact and stops multi-step AI work from declaring
success early, drifting off-task, or losing state. Same five pillars, two
install forms:

| Form                         | Where                                    | Control                                                                    |
| :--------------------------- | :--------------------------------------- | :------------------------------------------------------------------------- |
| **Runtime engine**           | any repo, any surface (CLI / HTTP / IDE) | graph-as-code: routing + gates + checkpoints (`solar-governor`, `.solar/`) |
| **`.github/` agent harness** | IDE-native Copilot                       | the classic prompt+agents form (installed via `solar-install.prompt.md`)   |

---

## Governor-as-graph runtime (current control layer)

The runtime, `solar-governor/`, is the deterministic control layer: LangGraph
nodes/edges route and gate, SQLite checkpoints make runs restart-safe, tools
are repo-bounded, and every dispatch writes a run-card. IDE-agnostic —
Copilot/VS Code is one client. Pilot-validated on the mandarin repo
(`solar-v5-wire`, kept as reference proof): driver-orchestrated chains,
T1–T5 PASS, epic-25 Phase A + verify close-out APPROVED, known-answer eval
battery 18/18. Chains are **driver-orchestrated** (agents never self-chain).

```bash
# runtime quick start (from this repo)
pip install ./solar-governor            # or: pip install -e ./solar-governor
solar-governor init --repo <target>      # write .solar/ config + registry
solar-governor doctor --repo <target>    # install self-check
solar-governor run "<task>" --chain epic --auto
solar-governor eval --repo <target>      # known-answer quality battery
```

Full design: [`docs/versions/v5.md`](docs/versions/v5.md) · concept:
[`docs/solar-ralph-concept.md`](docs/solar-ralph-concept.md) · harness visual:
[`docs/solar-agentic-harness.html`](docs/solar-agentic-harness.html).

The sections below describe the **`.github/` agent-harness form** (the
IDE-native Copilot install, still shipped and swappable via
`solar-install.prompt.md`); its runtime equivalents are mapped in
[`docs/versions/v5.md`](docs/versions/v5.md) §12.

---

## Why SOLAR-Ralph

| Pain Point                                                                | SOLAR Solution                                                                                                                            |
| :------------------------------------------------------------------------ | :---------------------------------------------------------------------------------------------------------------------------------------- |
| Agent declares the task done before it actually is                        | **Ralph Loop** — declarative exit condition + adversarial gate required before `TASK_COMPLETE` is written                                 |
| Agent starts implementing with missing context and fails mid-way          | **Material Gate** — `MATERIAL_INSUFFICIENT` signal stops the governor before any specialist is delegated                                  |
| Wrong direction: hours of code before you realize the agent misunderstood | **Design Gate** — user-approved plan must exist before any implementation agent runs                                                      |
| Can't trust AI output without independent verification                    | **Adversarial Bystander** — a non-author agent verifies at every write stage; bystander is a principle, not a named role                  |
| Session ends and the agent loses all progress                             | **Ledger** — sparse restart-safe state anchor in `.github/.ai_ledger.md` (Objective / Work Queue / Decisions Log); governor reads it cold |
| Swapping one agent breaks the whole team                                  | **Registry** — every agent is a YAML block in `AGENTS.md`; swap by updating one entry                                                     |

---

## The SOLAR Framework

| Layer | Role             | Implementation              | What It Does                                                                      |
| :---- | :--------------- | :-------------------------- | :-------------------------------------------------------------------------------- |
| **S** | **Specialist**   | `.github/agents/*.agent.md` | Isolated domain experts dispatched in parallel; one failure does not block others |
| **O** | **Orchestrator** | `.github/AGENTS.md`         | Pure event-driven governor; reads ledger stage, dispatches the right specialist   |
| **L** | **Ledger**       | `.github/.ai_ledger.md`     | Restart-safe state anchor; sparse, three sections, artifact links only            |
| **A** | **Adversarial**  | Review Auditors + Stop hook | Non-author verification before any write lands; bystander principle               |
| **R** | **Recursive**    | Ralph Loop + Stop hook      | Bounded iteration with a declarative exit condition and iteration cap             |

---

## Quick Start

**1. Install:** Open `solar-install.prompt.md` in VS Code agent mode and follow the prompts.

**2. Run your first task:** Open `#solar.prompt.md` in Copilot Chat agent mode.

📖 [Full setup guide](SOLAR-Ralph-implementation-guideline.md)

---

## What Gets Installed

- `.github/agents/` — 7 agents: Governor, Data Collector, Design Planning Architect, Implementation Specialist, Test Specialist, Docs Curator, Review Auditor
- `.github/skills/` — 7 skills: data-collection, design-planning, implementation, testing, doc-sync, review, recursive-remediation
- `.github/hooks/` — 2 core hooks: `post-tool-use` (adversarial VERIFY signal) + `stop` (completion gate). Six optional hooks (`pre-tool-use`, `user-prompt-submit`, `session-start`, `subagent-start`, `subagent-stop`, `pre-compact`) can be added per project.
- `.github/prompts/` — 2 prompts: `solar.prompt.md` (task entry) + `solar-registry-update.prompt.md`
- `.github/AGENTS.md` — Orchestration manifest: agent registry, skill index, hook config, ledger template
- `.github/.ai_ledger.md` — Persistent restart-safe state (Objective / Work Queue / Decisions Log). Governor resets from AGENTS.md Section 7 on TASK_COMPLETE.
- `.github/solar.config.json` — 5 behavior flags: `adversarial`, `learning`, `logging`, `human_approval`, `hooks`
- `.github/solar-system/` — Adversarial checklist, lifecycle protocols, handoff schemas

**Everything is swappable.** Add a specialist by dropping a new `.agent.md` file; attach a different skill to an existing agent the same way. No wiring changes anywhere else — run `#solar-registry-update.prompt.md` and the governor syncs the registry automatically.

---

## License

[MIT](LICENSE)
