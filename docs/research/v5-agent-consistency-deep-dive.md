# SOLAR V5: Consistency Deep-Dive — Priority Mechanisms

**Date:** 2026-08-16
**Status:** Deep research — concrete mechanisms for the 4 priority areas from `v5-agent-consistency-research-notes.md`
**Scope:** How each fix maps onto SOLAR V5.1.0's actual harness + the 2026 VS Code hook surface

---

## Key Discovery: The 2026 Hook Surface Changed Everything

The earlier notes assumed SOLAR's only enforcement lever was `PostToolUse`. The current VS Code agent hook system (verified Aug 2026) now exposes **eight lifecycle events**, and three of them are directly usable as _deterministic_ enforcement — not probabilistic prompting:

| Hook Event                       | Fires                     | Deterministic capability                                                    |
| -------------------------------- | ------------------------- | --------------------------------------------------------------------------- |
| `SessionStart`                   | First prompt of session   | Initialize/persist pinned state                                             |
| `UserPromptSubmit`               | Every user prompt         | **Inject context / re-assert instructions**                                 |
| `PreToolUse`                     | Before _any_ tool call    | **Block, approve, or rewrite a tool call** (`permissionDecision`)           |
| `PostToolUse`                    | After tool succeeds       | What SOLAR uses today (write-op → verify gate)                              |
| `PreCompact`                     | Before context compaction | **Export pinned state before truncation** (prevents implicit-contract loss) |
| `SubagentStart` / `SubagentStop` | Subagent spawn / complete | Per-agent isolation + cleanup                                               |
| `Stop`                           | Session ends              | Cleanup / report                                                            |

**Output contract** (JSON via stdout): `continue` (false = stop session), `stopReason`, `systemMessage` (warning to user), and event-specific `hookSpecificOutput` — e.g. `PreToolUse` accepts `permissionDecision: "allow" | "deny" | "ask"` for a _single_ tool call without killing the session.

**Exit codes**: `0` = success (parse stdout JSON); `2` = blocking error (stderr shown to model); other = non-blocking warning.

This means SOLAR can move from "prompt the agent to obey" to "the harness _cannot not_ obey."

---

## Priority 1 — Instruction Re-injection + Pinned Preamble

**Root cause (recap):** role-defining instructions get pushed into the "lost middle" (Liu et al. 2023) as history grows. Summarization drift then drops early constraints (existing note: `context-injection-and-token-runaway.md`).

**What SOLAR has:** Governor reads `AGENTS.md` at startup only; specialists are stateless and receive inline digests — but nothing re-asserts the _governor's own_ role constraints mid-session.

**Recommended mechanism:**

1. **`SessionStart` hook → write a pinned state file.** Extract objective + active constraints + open tasks into `.github/.solar_state.json` (100–300 tokens). This is the "Pinned State" tier from the 3-tier memory hierarchy — the one thing that survives compaction.
2. **`UserPromptSubmit` hook → re-inject the pinned preamble.** On every user turn, return `additionalContext` (or `systemMessage`) with the compact role block: identity, current ledger stage, active constraints. Cost is small (~150 tokens/turn), and it lands _near the generation point_ — the attention sweet spot.
3. **`PreCompact` hook → refresh the pinned state** before truncation so constraints are never lost to summarization drift. This directly fixes the "413 death spiral / summarization drift" failure mode documented in the existing notes.

**Effort:** Low — three small `.cjs` scripts reading/writing `.github/.solar_state.json`.

---

## Priority 2 — Deterministic Tool Gate + Dynamic Scoping

**Root cause (recap):** "don't use tool X" is a prompt; the model can still sample tool-X calls, and can _hallucinate_ access to tools it saw in other roles.

**What SOLAR has:** `post-tool-use.cjs` detects write-ops and emits `ADVERSARIAL_VERIFY_REQUIRED` — but it runs _after_ the tool, so it cannot prevent a forbidden tool call.

**Recommended mechanism:**

1. **`PreToolUse` hook → the deterministic tool gate.** Read the current dispatch's role from the ledger, consult the Agent Registry's tool allowlist, and return `permissionDecision: "deny"` (with `systemMessage` explaining why) for any tool not in that role's manifest. This runs _before_ execution — hallucinated or forbidden tool calls never happen, regardless of what the model "believes" it can access.
2. **Dynamic scoping in the registry.** Add a `tools_allowed` column to `AGENTS.md` §3 so the gate is data-driven, not hardcoded. The gate script reads role → allowlist at runtime.
3. **Exit-code-2 fallback.** If the gate cannot parse state, exit `2` so the model is _shown_ the block reason as context rather than silently proceeding.

**Why this beats prompt-only:** it is the exact "deterministic guardrail" the research recommends, and it directly eliminates problem behaviors #1 (tool-restriction decay) and #2 (hallucinated tool access).

**Effort:** Medium — one `PreToolUse` `.cjs` + a `tools_allowed` registry column + install-scaffold sync.

---

## Priority 3 — Fresh-Spawn Specialists + Structured Handoff

**Root cause (recap):** shared context bleeds role behavior; agent A's output style contaminates agent B's input (role drift / context contamination).

**What SOLAR has:** the right instincts — specialists are stateless, don't share `read`, and communicate only through sparse ledger + `verification-artifacts/`. This already _is_ fresh-spawn.

**Recommended mechanism (harden what exists):**

1. **`SubagentStart` hook → confirm isolation.** On spawn, assert the subagent receives only its own role preamble + digest; log the dispatch for audit. (Mostly a telemetry/assurance hook today.)
2. **`SubagentStop` hook → enforce the handoff contract.** Verify the subagent produced its declared artifact at the declared path; if missing, inject a non-blocking warning so the Governor re-dispatches.
3. **Keep the invariant, make it explicit in prompts:** the dispatch already says "each subagent is a stateless isolated session." Add one line to `solar.prompt.md` §3c: _never_ pass raw conversation — only `{task_id, refs[]}` + digest.

**Note:** The 2026 paper "Single-Agent LLMs Outperform Multi-Agent Systems" (2604.02460) actually _supports_ SOLAR's design — the failure mode is context fragmentation, which SOLAR avoids by isolating specialists. No architecture change needed; just enforce + telemetry.

**Effort:** Low — two small hooks + one prompt line.

---

## Priority 4 — Structured Output Contracts + Plan-Before-Execute

**Root cause (recap):** over long sessions the agent skips the plan step and jumps straight to execution (CoT degradation / plan-then-execute collapse).

**What SOLAR has:** the Ralph loop declares stages (Scan → Plan → Implement → Test → Verify), but the _reasoning_ inside each dispatch is unenforced.

**Recommended mechanism:**

1. **`PreToolUse` gate on write-ops:** require the ledger to be in the correct stage before a write-op tool is allowed. If the Governor tries to `editFiles` while the ledger stage is still `Scan`, deny and inject `systemMessage: "Plan stage not complete — dispatch Design Planning Architect first."` This makes plan-before-execute _structural_.
2. **`PostToolUse` structured-output validation:** after a specialist's final tool call, validate the produced artifact JSON against its sparse schema (`{task_id, refs[]}` + stage fields). Reject malformed output before the Governor advances the stage.
3. **Keep the prompt-level plan-then-execute instruction** (Plan-and-Solve pattern) as the soft layer, but make the hard gate the hook — so skipping the plan is mechanically impossible.

**Effort:** Medium — extend the existing write-op gate with a stage check + a schema validator.

---

## Synthesized V5 Design (concrete change set)

| #   | Change                                                                   | File                                           | Priority area |
| --- | ------------------------------------------------------------------------ | ---------------------------------------------- | ------------- |
| 1   | Add `PreToolUse` tool-gate hook (role allowlist + stage check)           | `.github/hooks/pre-tool-use.cjs`               | P2 + P4       |
| 2   | Add `SessionStart` + `PreCompact` pinned-state hooks                     | `.github/hooks/state-pin.cjs`                  | P1            |
| 3   | Add `UserPromptSubmit` preamble re-injection                             | `.github/hooks/preamble.cjs`                   | P1            |
| 4   | Add `SubagentStop` handoff-contract check                                | `.github/hooks/subagent-check.cjs`             | P3            |
| 5   | Add `tools_allowed` column to `AGENTS.md` §3 + `tools_allowed` per-agent | `template/.github/AGENTS.md`, all `*.agent.md` | P2            |
| 6   | Add pinned-state + re-injection notes to Governor prompt                 | `solar.prompt.md` §1, §3c                      | P1 + P3       |
| 7   | Update `hooks.json` to register all 5 hooks                              | `template/.github/hooks/hooks.json`            | all           |
| 8   | Keep installer in sync                                                   | `solar-install.prompt.md` + `template/`        | all           |

**Migration risk:** Low — all hooks are additive and passive when `hooks=false` (existing `solar.config.json` toggle). The `PreToolUse` gate is the only behavior-changing piece; gate it behind a `tool_gate` toggle defaulting to `true` but disable-able.

---

## Open Questions for Next Step

1. Should the tool-gate allowlist live in `AGENTS.md` (human-readable) or a machine-only `tools_allowlist.json`? (Recommend the latter — the registry stays human-readable, the gate reads JSON.)
2. Preamble re-injection frequency: every turn vs. only after compaction vs. only on stage change? (Recommend: every turn while cheap; add a stage-change trigger if token cost matters.)
3. Should `PreToolUse` gate also _approve_ safe ops automatically (replacing `human_approval` friction) — i.e. invert the default?

---

## Proven Implementations — Reference Check (2026-08-16)

Three reference points requested for the V5 design. Each informs a different layer of the change set.

---

### A. Mandarin repo — lightweight SOLAR (proven performance)

**Location:** `mandarin-vite-react-ts/.github/` (this workspace)

The mandarin repo runs a _lightweight_ adaptation of the same idea — it keeps orchestration + specialists + registry + skill index, but **drops the ledger, hooks, and adversarial artifacts entirely**. It is the "proven performance" reference because it is the actively-working system.

**What it keeps (and how it enforces without hooks):**

| Mechanism        | SOLAR-Ralph (heavy)                       | Mandarin (lightweight)                                                         |
| ---------------- | ----------------------------------------- | ------------------------------------------------------------------------------ |
| Orchestration    | `solar.prompt.md` Governor + ledger stage | `orchestrator.agent.md` with a **Delegation Map table**                        |
| Tool restriction | Hook-based (planned)                      | **Platform `tools:` frontmatter** — the agent literally lacks the tool         |
| Role isolation   | Stateless digest handoff                  | Same — `runSubagent` + no shared state                                         |
| Rules            | Ledger + prompts                          | **`prohibitions:` list** in `AGENTS.md` frontmatter + `## Constraints` in body |
| State anchor     | `.ai_ledger.md`                           | None — stateless, re-derived each turn                                         |

**The critical finding for Priority 2:** the mandarin agents declare `tools:` in `.agent.md` frontmatter (e.g. Architect has no `edit`/`execute`/`agent`; only `vscode, read, search, web, browser, codegraph/*, todo`). VS Code enforces this **before** the model ever sees the tool — this is _platform-level dynamic tool scoping_, the exact mechanism Priority 2 recommends, already proven in production. No hook script needed for the "agent can't even request a forbidden tool" case.

**Two implications for V5:**

1. **Prefer the platform `tools:` field over a `PreToolUse` hook for _static_ role tool-scoping.** The hook is still needed for _dynamic_ cases (stage-dependent allowlists, cross-cutting write-op guards), but static per-role allowlists should be declared declaratively — it is simpler, faster, and already proven.
2. **The mandarin repo shows a lighter floor is viable.** A "SOLAR-Lite" mode (registry + skill index + `tools:` scoping + `runSubagent` delegation map, no ledger/hooks) could be the default install, with hooks as an opt-in "hardened" layer. This reduces install friction and matches the proven path.

**Delegation Map pattern** (from `orchestrator.agent.md`) is a concrete win: a single table mapping _"when user asks to X → route to Agent Y"_ + a chained workflow ("research → plan → implement → docs → review"). More maintainable than the Governor's inline stage loop for the common case.

---

### B. DeepSeek Harness (`dsh`) — plugin architecture + npx install

**Repo:** `github.com/deepseek-ai/deepseek-harness` — 128k★ / 12.7k forks, TypeScript monorepo.

**Key facts (verified Aug 2026):**

- **"Everything is a plugin"** architecture, powered by **Cordis** (plugin framework with spatiotemporal composability).
- **One-line install/run:** `npx @deepseek-ai/dsh web` → starts Web UI at `http://127.0.0.1:3080`. Also runnable from source (`pnpm install && pnpm run build && pnpm dsh web`).
- Ships `AGENTS.md` + `CLAUDE.md`; plugins discoverable via the `dsh-plugin` GitHub topic; multi-language (`packages/`, `native/`, `python/`, `apps/`).
- **Status:** developer preview, "compatibility-breaking changes expected."

**Relevance to SOLAR V5 (two directions):**

1. **Plugin model is the natural end-state for SOLAR's "everything is swappable" claim.** SOLAR today swaps agents/skills by editing registry rows. A plugin contract (drop a folder = add a specialist + its skill + its tool allowlist) would let the registry auto-populate from the filesystem instead of manual `solar-registry-update`. The `dsh-plugin` topic convention (self-describing plugins) is worth copying.
2. **`npx` distribution is the installation answer** (see C below). DeepSeek proves a harness can ship as a single npm package with a zero-config `npx` entry point.

**Caution:** DeepSeek Harness is a _runtime_ harness (its own Web UI + server), not a _prompt-scaffold_ harness like SOLAR. SOLAR's differentiator — no custom runtime, lives entirely in `.github/` as native Copilot config — is a feature, not a gap. Borrow the plugin _conventions_ and the _npx distribution_, not the runtime.

---

### C. Installation enhancement — npx / one-line install

**Current state (verified):** SOLAR's install is **not** one-line. `README.md` says "Open `solar-install.prompt.md` in VS Code agent mode and follow the prompts" — a human-in-the-loop agent scaffold, not a command. There is no `package.json`, no npm package, no CLI.

**Reference patterns that achieve true one-line install:**

| Project              | One-line command                     | Mechanism                 |
| -------------------- | ------------------------------------ | ------------------------- |
| **DeepSeek Harness** | `npx @deepseek-ai/dsh web`           | npm package + `bin` entry |
| **Claude Code**      | `npm i -g @anthropic-ai/claude-code` | npm global install        |
| **Copilot CLI**      | `npm i -g @github/copilot`           | npm global install        |

**Recommended path for SOLAR (lowest-friction, matches architecture):**

1. **`npx @solar-ralph/cli install`** — a thin Node CLI (no dependencies beyond Node) that:
   - Copies `template/` → target repo `.github/` (agents, skills, hooks, prompts, `AGENTS.md`, `solar.config.json`, ledger).
   - Runs the same `[FILL IN]` token substitution the install prompt does, driven by a short interactive prompt (or `--stack=…` / `--non-interactive` flags).
   - Writes `solar_version` into `AGENTS.md` (release checklist item #3).
2. **Keep `solar-install.prompt.md` as the fallback** for environments where `npx` is unavailable (restricted MCP / no Node) — the two paths must stay in sync (installer-authoring invariant).
3. **`npx @solar-ralph/cli` with no args** → print usage + "detect this repo" mode; `install` subcommand does the scaffold; `update` re-syncs from a newer template version.

**Effort:** Medium — extract the inventory file into a CLI source-of-truth (or have the CLI read `solar-install-inventory.md` directly to avoid two sources of truth). The install prompt and the CLI must both read the _same_ inventory.

---

## Updated Recommended Sequencing (after reference check)

1. ⭐ **Platform `tools:` scoping per agent** (Priority 2, static part) — copy the proven mandarin pattern; zero hook code.
2. ⭐ **`PreToolUse` hook** for the _dynamic_ gate (stage-dependent + write-op guard) (Priority 2, dynamic part).
3. ⭐ **Pinned-state trio** (`SessionStart` + `UserPromptSubmit` + `PreCompact`) (Priority 1).
4. ⭐ **`npx` install CLI** (installation) — unlocks adoption; reads the same inventory.
5. **Delegation Map table** in the Governor (borrow from mandarin) — readability win, low risk.
6. **Plugin contract / registry auto-discovery** (borrow from DeepSeek) — medium-term.
7. **Stage gate + SubagentStop telemetry** (Priority 4 + 3) — after the above stabilize.

---

_End of deep-dive. Recommend scheduling the P2 tool-gate first (highest leverage, smallest surface), then P1 pinned-state, then P4 stage gate, then P3 telemetry._
