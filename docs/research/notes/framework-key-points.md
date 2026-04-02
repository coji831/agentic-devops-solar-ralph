# Framework Research — Key Points

Extracted from `docs/research/framework/`. One line per finding, linked to source section.

---

## SOLAR-Ralph Framework v1

Source: [SOLAR-Ralph-Framework-v1.md](../framework/SOLAR-Ralph-Framework-v1.md)

### Specialist (S)

- Agent Skills use "just-in-time" loading — only loaded when relevant, keeping context window clean. → [Agent Skills and Procedural Knowledge](../framework/SOLAR-Ralph-Framework-v1.md#agent-skills-and-procedural-knowledge)
  - **✅ Implemented.** `.github/skills/*/SKILL.md` structure in place; skills loaded on demand.
- `.agent.md` `tools` property isolates what a specialist can touch — prevents doc agent from executing terminal commands. → [Custom Agents and Role-Based Personalization](../framework/SOLAR-Ralph-Framework-v1.md#custom-agents-and-role-based-personalization)
  - **✅ Implemented.** Auditors and security agent have `tools: [read, search, execute]`; governor has full set including `agent`.

### Orchestrator (O)

- Hub-and-spoke: governor keeps high-level view, delegates to workers with focused context windows — avoids context window exhaustion. → [Hierarchical Multi-Agent Architectures (HMAS)](../framework/SOLAR-Ralph-Framework-v1.md#hierarchical-multi-agent-architectures-hmas)
  - **✅ Implemented.** Governor + 13 specialists; tiered context gate prevents over-reading.
- `AGENTS.md` + `copilot-instructions.md` are the governance root for the Plan Agent. → [Strategic Planning and Task Decomposition](../framework/SOLAR-Ralph-Framework-v1.md#strategic-planning-and-task-decomposition)
  - **✅ Implemented.** Both files exist; AGENTS.md marked always-on in governor, copilot-instructions.md platform-injected.

### Ledger (L)

- Copilot Memory validates stored memories against current code state before use ("just-in-time verification") — prevents stale context from corrupting decisions. → [Agentic Memory and Repository Insights](../framework/SOLAR-Ralph-Framework-v1.md#agentic-memory-and-repository-insights)
  - ~~⚠️ Gap.~~ **✅ Not applicable.** `repo/memory` pattern retired. `.github/instructions/*.instructions.md` replaces it as always-on context via `applyTo` globs — no manual invocation or JIT verification needed.
- Event-driven ledger model: every tool call and LLM response is one event — enables state projection without drift. → [The Ledger as an Event Log](../framework/SOLAR-Ralph-Framework-v1.md#the-ledger-as-an-event-log)
  - 🚫 **Not implemented — deliberate simplification.** Phase 1 Required Simplifications explicitly chose markdown ledger over event stream. Full event sourcing deferred indefinitely; markdown is sufficient for restart-safe state and avoids tooling overhead.

### Adversarial (A)

- Auditor is prompted to _find flaws_, not assist the Specialist — sycophancy mitigation by design. → [Sycophancy Mitigation and Linear Interventions](../framework/SOLAR-Ralph-Framework-v1.md#sycophancy-mitigation-and-linear-interventions)
  - **✅ Implemented.** Both review auditors describe themselves as adversarial challengers; security auditor explicitly constrained not to assume safety from passing tests.
- Adversarial component blocks task progression if tests, static analysis, or ledger cross-check fail — backpressure. → [Backpressure and Soundness Checks](../framework/SOLAR-Ralph-Framework-v1.md#backpressure-and-soundness-checks)
  - **✅ Implemented.** Governor step_supervision check #4 blocks pipeline on critical gaming findings; review stage rule: "NEVER skip the Review stage."

### Recursive (R)

- Ralph Wiggum technique: prompt never changes, environment (files) evolves each loop until completion promise is met. → [The Ralph Loop Architecture](../framework/SOLAR-Ralph-Framework-v1.md#the-ralph-loop-architecture)
  - **✅ Implemented.** `stop.cjs` enforces loop continuation; ledger state persists across turns. Platform limitation: original prompt isn't literally re-injected — ledger state substitutes as continuity anchor.
- Stop hook blocks agent exit if completion promise absent — forces continuation; costs premium requests. → [Agent Hooks and Lifecycle Automation](../framework/SOLAR-Ralph-Framework-v1.md#agent-hooks-and-lifecycle-automation)
  - **✅ Implemented.** `stop.cjs` returns `{ continue: true, systemMessage }` when `Completion Promise: pending` detected in ledger.
- Hook event table: `preToolUse` = permission/security gate; `postToolUse` = ledger update; `stopHook` = recursive governor. → [Agent Hooks and Lifecycle Automation](../framework/SOLAR-Ralph-Framework-v1.md#agent-hooks-and-lifecycle-automation)
  - **✅ By design.** `preToolUse` ✅ (Stage 1 enforcement gate). `stopHook` ✅ (recursive governor). `postToolUse` runs `tsc --noEmit` backpressure as intended. Ledger is written directly by agents — more reliable than a hook doing it; no gap here.

### Configuration Hierarchy

- Priority order: Personal > Path-specific > Repository-wide > Agent > Organization. → [Repository-Level Instructions and Rules](../framework/SOLAR-Ralph-Framework-v1.md#repository-level-instructions-and-rules)
  - **✅ Implemented.** AGENTS.md defines explicit 6-level precedence; path-specific instructions in `.github/instructions/frontend.instructions.md` and `backend.instructions.md`.

---

## SOLAR-Ralph Framework v3

Source: [SOLAR-Ralph-Framework-v3.md](../framework/SOLAR-Ralph-Framework-v3.md)

### Paradigm Shift

- 2026: "AI as text" deprecated → "AI as execution" — agents must be embedded in infrastructure, not just suggest code. → [The Paradigm of Agentic Execution and Infrastructure](../framework/SOLAR-Ralph-Framework-v3.md#the-paradigm-of-agentic-execution-and-infrastructure)
  - **✅ Implemented.** Entire SOLAR harness (hooks, pipelines, ledger, loop) is execution-first.
- Multi-agent orchestration requires managing asynchronous subagents and stateful graphs, not linear chains. → [The Paradigm of Agentic Execution and Infrastructure](../framework/SOLAR-Ralph-Framework-v3.md#the-paradigm-of-agentic-execution-and-infrastructure)
  - **⚠️ Gap.** Pipeline stages are strictly sequential; no parallel subagent execution. Governor delegates one specialist at a time.

### Adaptive Specialists

- Specialists defined via `.agent.md` profiles — persona-driven, not prompt-driven. Tool isolation via `tools` property. → [Personas and Adaptive Specialist Profiles](../framework/SOLAR-Ralph-Framework-v3.md#personas-and-adaptive-specialist-profiles)
  - **✅ Implemented.** 16 `.agent.md` profiles in `.github/agents/`.
- Path-specific instructions allow different rules for frontend vs. backend in the same monorepo. → [Personas and Adaptive Specialist Profiles](../framework/SOLAR-Ralph-Framework-v3.md#personas-and-adaptive-specialist-profiles)
  - **✅ Implemented.** `frontend.instructions.md` and `backend.instructions.md` with scoped `applyTo` globs.

### Pipeline & CI/CD

- GitHub Agentic Workflows: Markdown natural language files compile to locked GitHub Actions YAML — no branching logic needed. → [Agentic Workflows and Natural Language Orchestration](../framework/SOLAR-Ralph-Framework-v3.md#agentic-workflows-and-natural-language-orchestration)
  - **❌ Not implemented.** System is VS Code agent-based. No GitHub Actions agentic workflows configured.
- Guardrails: agents are read-only by default; writes route through reviewable "safe outputs"; rate limits prevent runaway loops. → [Guardrails, Sandboxing, and Governance](../framework/SOLAR-Ralph-Framework-v3.md#guardrails-sandboxing-and-governance)
  - **⚠️ Partial.** `tools` isolation and `preToolUse` gate exist. No rate limiting on agent delegation calls.

### MCP

- MCP is the universal connectivity layer — not a feature, a foundational requirement; transferred to Linux Foundation (Dec 2025). → [Model Context Protocol (MCP) as the Interoperability Standard](../framework/SOLAR-Ralph-Framework-v3.md#model-context-protocol-mcp-as-the-interoperability-standard)
  - **⚠️ Partial.** `.vscode/mcp.json` configures 4 servers (Playwright, Puppeteer, Fetch, GitHub). Not universally adopted — only specific skills (browser-reproduction, external-integration-operations) leverage MCP actively.
- Three core MCP primitives: Resources (read-only context), Tools (executable actions), Prompts (reusable templates). → [Architecture and Core Primitives of MCP](../framework/SOLAR-Ralph-Framework-v3.md#architecture-and-core-primitives-of-mcp)
  - **⚠️ Partial.** Only Tools primitive formally configured in `mcp.json`. Resources and Prompts primitives not modeled.
- MCP "Tasks" primitive (SEP-1686): call-now/fetch-later pattern for long-running operations that survive disconnections. → [Architecture and Core Primitives of MCP](../framework/SOLAR-Ralph-Framework-v3.md#architecture-and-core-primitives-of-mcp)
  - ❌ **Platform dependency — outside SOLAR control.** SEP-1686 is on the MCP roadmap but not yet available in VS Code Copilot. SOLAR will adopt when the platform ships it; no action needed on our side.

### Memory

- Memory layer supports episodic, semantic, and working memory — uses vector databases for long-horizon recall. → [Memory Substrate and Contextual Continuity](../framework/SOLAR-Ralph-Framework-v3.md#memory-substrate-and-contextual-continuity)
  - **⚠️ Gap.** Memory uses flat markdown files (`/memories/repo/*.md`). No vector database, no episodic/semantic/working memory tiering. Template ships with no `memories/` directory — must be created post-install.
- PLAN.md and AGENTS.md committed to version control = handoff protocol for multi-agent, multi-session tasks. → [Leveraging Tribal Knowledge through Documentation](../framework/SOLAR-Ralph-Framework-v3.md#leveraging-tribal-knowledge-through-documentation)
  - **⚠️ Partial.** No PLAN.md. `.ai_ledger.md` (template committed) serves as the handoff mechanism instead — equivalent in practice but structurally different.

### Security

- Zero Trust for agentic execution: every tool call explicitly authorized and audited. → [Securing the Agentic Infrastructure](../framework/SOLAR-Ralph-Framework-v3.md#securing-the-agentic-infrastructure)
  - **⚠️ Partial.** `preToolUse` gates agent delegation calls; `tools` isolation restricts per-agent capabilities. No audit logging of individual tool calls; no fine-grained IAM-style authorization beyond tool lists.
- "Capabilities overhang": model power exceeds safe deployment ability — requires kill switches and human feedback loops. → [Managing the Capabilities Overhang](../framework/SOLAR-Ralph-Framework-v3.md#managing-the-capabilities-overhang)
  - **✅ Implemented.** `solar.config.json` provides per-hook kill switches, global `solar.active` flag, and bootstrap mode bypass. Human is always in the loop for plan approval.

---

## SOLAR Pipeline Contrast

Source: [SOLAR-Pipeline-Contrast.md](../framework/SOLAR-Pipeline-Contrast.md)

- Pipeline contract lives in AGENTS.md or orchestrator `.agent.md` — defines stage sequence and skip conditions. → [Orchestrator Configuration](../framework/SOLAR-Pipeline-Contrast.md#1-orchestrator-configuration-githuborchestratorconfiguration-githubagentstorchestratorn.agent.md)
  - **✅ Implemented.** All 4 pipeline contracts defined in AGENTS.md; governor reads and executes them.
- Investigation stage produces a "gradient signal" — simple correction skips Design phase, architectural change invokes it. → [Investigation and Conditional Routing](../framework/SOLAR-Pipeline-Contrast.md#i-investigation--conditional-routing)
  - **✅ Implemented.** Pipeline 3 (Bug Fix) in AGENTS.md: "simple root cause → skip stage 2, go to stage 3."
- Backpressure enforcement: loop cannot exit until `npm test` / `build` pass — completion promise is the only exit key. → [The Recursive Loop Mechanism](../framework/SOLAR-Pipeline-Contrast.md#ii-the-recursive-loop-mechanism)
  - **✅ Implemented.** `postToolUse` runs `tsc --noEmit` on writes. `stop.cjs` also blocks loop exit if `Verification: FAIL` is detected in the ledger — agent cannot write a completion promise without first resolving test failures.
- Adversarial auditors specifically probe for "gaming" — agents that pass tests without fixing the underlying problem. → [Adversarial Review and Repair](../framework/SOLAR-Pipeline-Contrast.md#iii-adversarial-review--repair)
  - **✅ Implemented.** ARA gaming check in both review auditor progress protocols; governor step_supervision check #4 explicitly handles gaming.
- Stop hook exits with code 2 if `WORK_PACKAGE_COMPLETE` is absent — re-injects original prompt and forces continuation. → [State Continuity and Scar Tissue](../framework/SOLAR-Pipeline-Contrast.md#iv-state-continuity--scar-tissue)
  - **⚠️ Platform adaptation.** VS Code hooks use JSON stdout protocol (`{ continue: true }`), not bash exit codes. Functionally equivalent — hook returns `continue: true` to force continuation; platform re-injects context.
- `Session-Type: loop` in ledger prevents other agents from interrupting a write-heavy loop session. → [The Recursive Loop Mechanism](../framework/SOLAR-Pipeline-Contrast.md#ii-the-recursive-loop-mechanism)
  - **✅ Implemented.** All hooks check `Session-Type` from ledger; bootstrap mode and chat mode bypass enforcement.
