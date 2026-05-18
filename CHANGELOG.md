# CHANGELOG

All notable changes to the SOLAR-Ralph framework are documented here.
Format: newest version first. Each entry covers what changed from the previous version and why.

---

<!-- RELEASE CHECKLIST (run before each release):
  1. Re-verify tool-set names in all template `*.agent.md` `tools:` frontmatter against VS Code Copilot docs:
     https://code.visualstudio.com/docs/copilot/customization/custom-agents
     Update if any name changed between VS Code releases.
  2. Re-verify hook field names against: https://code.visualstudio.com/docs/copilot/customization/hooks
  3. Bump version in this file and in solar-install.prompt.md header.
-->

---

## v4.6 patch — May 6, 2026

**Theme:** Template + install prompt alignment — consistency fixes across `template/`, `solar-install.prompt.md`, and all reference docs.

### Changed

- **`template/.github/solar.config.json`** — `hooks` default changed to `true` (hooks active on install). Removed `_ref` documentation comment key (clean JSON).
- **`template/.github/AGENTS.md` Section 6** — Added optional hooks list (`pre-tool-use`, `user-prompt-submit`, `session-start`, `subagent-start`, `subagent-stop`, `pre-compact`) with instruction to register in `hooks.json`. Fixed toggle key `hooks.enabled` → `hooks`.
- **`template/.github/AGENTS.md` Section 7** — Added `Completion Promise: pending` line to ledger template block (required for `stop.cjs` to fire correctly).
- **`solar-install.prompt.md` Step 5D** — Added optional hooks paragraph listing the 6 non-core hooks and how to register them.
- **`concept.md`** — Updated hooks default description: hooks are on by default (`"hooks": true`); set `false` to disable.
- **`SOLAR-Ralph-implementation-guideline.md`** — Corrected hooks toggle syntax and noted hooks-on default. Replaced `parallel_dispatch` with `hooks` in config flags table.
- **`template/.github/AGENTS.md` Section 8** — Removed `parallel_dispatch` flag (not implemented).
- **Ledger reset protocol** — Governor now resets `.ai_ledger.md` from AGENTS.md Section 7 Ledger Template block (no separate `.ai_ledger.template.md` file required).

---

## v4 — April 27, 2026

**Theme:** Concept harness alignment — stripped v4-specific complexity back to minimal SOLAR harness.

### Added

- **`solar-install.prompt.md`** — single interactive installer replaces all `/solar-setup-*` prompts. One file, run in VS Code agent mode, builds the full system end-to-end.
- **`solar-registry-update.prompt.md`** — dedicated registry sync prompt; updates `AGENTS.md` after any component add/swap/remove.
- **Base-install skills** — `data-collection`, `design-planning`, `implementation`, `testing`, `review`, `recursive-remediation` (generic tier, stack-agnostic). Previously only stack-specific skills shipped.
- **Base-install agents** — `review-auditor` and `test-specialist` (generic tier) added alongside existing stack-specific specialists.
- **Communication Discipline rule** — `solar.instructions.md` now includes a `## Communication Discipline` section: work silent, signal only. Three permitted outputs: stage signals, BLOCKED notices, final artifacts. No narration, no preamble. Rule also embedded in installer Step 5E so every new installation generates it.
- **`docs/versions/v4.md`** — full system state snapshot: base install (7+7+2), full agent roster (21), full skill roster (19), hook set, config flags, what changed from v3, and deferred items.
- **`docs/solar-component-diagram.md`** — visual layer diagram.
- **`.github/solar-system/learnings/README.md`** and **`logs/README.md`** — optional component activation stubs.

### Changed

- **`solar.config.json`** — reduced from multi-key v4 format to 5 flags: `adversarial`, `learning`, `logging`, `human_approval`, `parallel_dispatch`. Removed `solar.active` (SOLAR is active when files are present, no flag needed).
- **`solar.instructions.md`** — removed dead `.github/guides/` references; removed `/solar-setup-*` commands and `solar.active` activation block; simplified Setup section to point to installer; simplified Key Files to actual install output.
- **`AGENTS.template.md`** — updated to 9-section installer structure matching `solar-install.prompt.md` output; added Communication Discipline reference in Section 9.
- **`.ai_ledger.template.md`** — updated 5-section sparse format; references `hooks.enabled` instead of `solar.active`.
- **`SOLAR-Ralph-implementation-guideline.md`** — rewritten as 6-section install-focused reference (Install / What Gets Installed / First Task / Registry Sync / Optional Components / Config Reference). No scripts, no setup prompts.
- **`README.md`** — rewritten: problem → SOLAR solution table replaces feature list; swappable registry callout with `#solar-registry-update.prompt.md`; "What Gets Installed" section with exact 7/7/2 counts.
- **`copilot-instructions.template.md`** — removed `/solar-setup-quick` and `solar.active` from checklist.
- **`.template.gitignore`** — added optional component paths for learnings and logs.

### Removed

- **`.github/guides/`** — all 4 operator guides moved to `docs/knowledge-base/` (content preserved, not deleted).
- **v4 solar-system internals** — `solar-system/context/` (4 files), `solar-system/patterns/output-position-contract.md`, `solar-system/schemas/handoff-types.md`, `solar-system/schemas/workflow-metadata.schema.json` moved to `docs/knowledge-base/` with `v4-` prefix.
- **10 setup and utility prompts** — `/solar-setup-quick`, `/solar-setup-full`, `/solar-setup-scan-repo`, `/solar-setup-apply-config`, `/solar-setup-instructions`, `solar-compound-review`, `solar-audit-story`, `solar-promote-learning`, `solar-cleanup-learning`, `solar-enter/exit-bootstrap`.
- **4 workflow files** — `pipelines/` and `workflows/` folders removed (pipeline definitions moved into governor agent and AGENTS.md).
- **`scripts/` folder** — 5 scripts removed (`install-solar.ps1`, `install-solar.sh`, `hook-test-runner.ps1`, `check-hook-test-results.ps1`, `solar-manifest.txt`).
- **`.github/solar-system/.learnings/`** — 10 files removed; replaced by `learnings/README.md` stub (opt-in, activated by `"learning": true`).
- **`solar-system/workflow-migration-map.md`** and **`solar-system/context/effort-simulation.md`**.

### Research basis

- [SOLAR-Ralph v4 Framework](docs/research/framework/SOLAR-Ralph-framework-v4.md)
- [v4 Feedback](docs/research/feedback/SOLAR-Ralph-v4-feedback.md)
- [v4 Feasibility Analysis](docs/research/notes/v4-feasibility-analysis.md)
- [Deep Scan Report 2026-04-23](verification-artifacts/solar-ralph-deep-scan-report-2026-04-23.md)
- [v4 System State](docs/versions/v4.md)

---

## v3 — April 2, 2026

**Theme:** Harness hardening for low-reasoning model governors (Claude Haiku 4.5).

### Added

- **PreToolUse hook** (`.github/hooks/pre-tool-use.cjs`) — mechanical gate that blocks `agent` tool calls if Stage 1 (Design Planning Architect) has not completed for the current pipeline. Bypasses Design/Architect/Bug Investigation targets. Addresses the "agentic impulse" failure mode where governors skip Stage 1 to jump directly to implementation.
- **14 skills** — `story-execution`, `doc-sync`, `memory-curation`, `memory-verification`, `recursive-remediation`, `browser-reproduction`, `external-integration-operations`, `release-governance` added on top of the v2 base skills.
- **Release Readiness Specialist** agent — Go/No-Go gate invoked by governor before Pipeline 3 and 4 close. Verifies tests, security audit, docs, AC, and ledger state.
- **Cache and External Integration Specialist** agent — owns Redis, HTTP clients, and third-party API integration work.
- **Solar Bootstrap** and **Solar Scan Collector** agents — setup utilities that bypass SOLAR governance entirely.
- **`solar.config.json`** — centralized kill switch and mode configuration. Modes: `simple`, `loop`, `plan`, `manual-test`, `bootstrap`.
- **Tiered context gate in governor** — replaced blanket "read 4 docs before delegating" with pipeline-specific minimum reads. Knowledge=0, Simple Fix=1, Bug Fix=1+mentioned files, Feature=3. Prevents context window bloat (malloc/free problem).
- **Binary Stage 4 trigger** — Security Auditor stage is now triggered by exact file-pattern match (`*route*`, `*auth*`, `*middleware*`, `*config*`, `*controller*`, `*permission*`, `*secret*`, `*credential*`), not qualitative judgment.
- **Ledger close template** — literal block with all required fields added to governor `<output_format>`. Prevents schema drift at pipeline close in long sessions.
- **`grep_search`/`file_search` preference rule** — added to all 12 specialist agents. `semantic_search` demoted to last resort due to confirmed VS Code bug causing up to 7-minute hangs in nested subagent environments (issue #299102).

### Changed

- **Governor model** — changed from single-model to dual config: Claude Haiku 4.5 (primary) + Claude Sonnet 4.5 (fallback). Haiku 4.5 chosen for cost/throughput; Sonnet 4.5 available for complex orchestration.
- **Governor delegation indicator** — removed `| model: <model>` segment. Platform does not reliably read subagent frontmatter at dispatch (GitHub issues #18873, #19402).
- **Stop hook** — now checks `Session-Type` field in ledger; only enforces loop continuation in `loop` mode. Silent on `chat` and `manual-test`.
- **PostToolUse hook** — filtered to write operations only; runs `tsc --noEmit` as backpressure in `loop` mode.

### Research basis

- [Improving Low-Reasoning Model Performance](docs/research/notes/improving-low-reasoning-model-performance.md)
- [SOLAR-Ralph Framework v3](docs/research/framework/SOLAR-Ralph-Framework-v3.md)
- [Phase 2 Feedback](docs/research/feedback/SOLAR-Ralph-phase-2-feedback.md)
- [Governor Haiku Fix Plan](docs/work-logs/governor-haiku-fix-plan.md)

---

## v2 — Early 2026

**Theme:** Pipeline formalisation and quality enforcement from Phase 1 feedback.

### Added

- **4 canonical pipelines** in `AGENTS.md` — Knowledge, Simple Fix, Bug Fix, Feature. Replaced advisory delegation rules with Mandatory Delegation Matrix.
- **Pipeline Selection table + Step-Level Process Supervision** in governor — 4-point check (structural, logic path, scope, code-gaming) after every delegated stage before advancing.
- **Reflexion cycles** in `frontend-feature-implementation` and `backend-feature-implementation` skills — Responder → Evaluator → Revisor inner loop before output.
- **ARA code-gaming detection** in both review auditor agents and both review skills — detects test suite modification to pass rather than fix the underlying bug.
- **Semantic Gradient enforcement** — `AGENTS.md` Verification Contract and `.ai_ledger.md` mandate `Root Cause Hint` with semantic direction on failures, not just "failed."
- **Memory verification skill** — validates stale `/memories/repo/` facts against current codebase before applying.
- **PostToolUse backpressure** — `tsc --noEmit` runs on writes in loop mode; compiler errors injected as context.
- **Reproduction Script Contract** in Bug Investigation Specialist — writes minimal `curl`/Vitest repro script and confirms failure before classifying root cause.
- **Session-Type field** in `.ai_ledger.md` — `chat` / `loop` / `manual-test` drives hook behavior.
- **`ralph-loop.prompt.md`** and **`audit-story.prompt.md`** commands promoted from Phase 2 to Phase 1.
- **Tiered model routing** — Bug Investigation Specialist on Claude Haiku 4.5 with full exploration toolset.
- **MCP servers** (`.vscode/mcp.json`) — Playwright, Puppeteer, Fetch, GitHub MCP configured.
- **`browser-reproduction` skill** — browser-based bug reproduction via Playwright/Puppeteer.
- **Path-specific instruction files** — `apps/frontend/.instructions.md` and `apps/backend/.instructions.md` with scoped `applyTo` patterns.

### Research basis

- [Phase 1 Feedback](docs/research/feedback/SOLAR-Ralph-phase-1-feedback.md)
- [Phase 2 Feedback](docs/research/feedback/SOLAR-Ralph-phase-2-feedback.md)
- [SOLAR Pipeline Contrast](docs/research/framework/SOLAR-Pipeline-Contrast.md)

---

## v1 — 2025

**Theme:** Initial SOLAR-Ralph system — five pillars, flat specialist pool.

### Established

- **SOLAR architecture** — Specialist, Orchestrator, Ledger, Adversarial, Recursive pillars.
- **Hub-and-spoke orchestration** — Orchestration Governor as central hub, flat pool of frontend/backend/test/review/security/docs specialists.
- **Initial agent set (11 agents):** governor, design-planning-architect, bug-investigation-specialist, frontend-impl, frontend-review, frontend-test, backend-impl, backend-review, backend-test, security-auditor, docs-curator.
- **Base skills (6):** frontend-feature-implementation, frontend-review, frontend-testing, backend-feature-implementation, backend-review, backend-testing.
- **Ledger** — `.github/.ai_ledger.md` for restart-safe execution state.
- **Repo memory** — `/memories/repo/` with facts files: commands, architecture, workflow, frontend, backend, security, verification.
- **Hooks** — UserPromptSubmit, PostToolUse, Stop in `hooks.json`.
- **`AGENTS.md`** — hub-and-spoke contract, initial delegation rules.
- **Knowledge base** — agent-orchestration-patterns, adversarial-auditing-patterns, recursive-refinement-patterns, agent-memory-governance.
- **Operator guides** — solar-ralph-workflow, agent-operations-guide, memory-governance-guide.

### Research basis

- [SOLAR-Ralph Framework](docs/research/framework/SOLAR-Ralph-Framework.md)
- [Rollout Plan](docs/work-logs/solar-ralph-rollout-plan.md)
