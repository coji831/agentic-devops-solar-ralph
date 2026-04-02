# CHANGELOG

All notable changes to the SOLAR-Ralph framework are documented here.
Format: newest version first. Each entry covers what changed from the previous version and why.

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
