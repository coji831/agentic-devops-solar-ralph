# SOLAR-Ralph — Open TODOs

Tracks deferred decisions and known gaps across all versions.
Add new items under the relevant version section. Resolved items stay in the file marked **Resolved**.

---

## How to use this file

- Each item has a unique ID: `TD-<version>-<seq>` (e.g. `TD-4-1` = v4 item 1).
- Status: **Open** | **Resolved** | **Deferred** | **Superseded**
- Add new items at the bottom of the relevant version section.
- Do not remove resolved items — mark them resolved with a date.

---

## v5 — Governor-as-graph (LangGraph)

### TD-5-1: v5 plan — governor-as-graph (LangGraph)

**Status:** Resolved 2026-09-05 — shipped as v5.3.0 (governor-as-graph runtime). B2 evals PASS; B3 mandarin pilot (`solar-v5-wire`, reference only) T1–T5 PASS + epic-25 delivery + verify close-out APPROVED; eval battery 18/18 across tuning settings.
**Summary:** `docs/versions/v5.md` defines the v5 plan — LangGraph control layer (governor-as-graph), state schema grounded on the REAL 3-section ledger (Objective/Work Queue/Decisions Log; docs' 5-section claim was drift), specialist registry + compactor nodes, light/full profiles, one-engine 4-front install (`uvx`/`npx solar-governor init --profile`, container, CI action), verifiability (install `doctor` + operational eval), data sovereignty (repo-bounded by default, hub uplink opt-in for owned repos only), v4→v5 migration (steps 1–8).
**Prototype:** `experiments/governor-graph/` — 6 evals (interrupt, checkpoint-resume, deterministic routing, streaming, hub KB MCP call, compactor). Decision gate after B2.
**Supersedes:** TD-4-1/2/3/4 (effort steering → model routing), TD-4-5 (routing policy → graph edges).

## v5.4.x — Backlog (opened after v5.3.1 from the real epic-25 pilot on mandarin main; v5.4.0 shipped TD-5.4-1 — TD-5.4-2..7 remain open)

### TD-5.4-1: ~~Per-node model routing~~

**Status:** Resolved 2026-09-18 — shipped in **v5.4.0**. Resolution is `SOLAR_MODEL` env → role `model` → `cfg.model` → default; an empty value at any level is skipped, so a registry that leaves `model` as `""` keeps inheriting exactly as before. `graph._role_spec` was returning `(role, system)` only and dropping every other key, so no role spec could reach the executor at all — it now returns the full dict, with a `_role_prompt` helper and both call sites updated. `write_handoff` also takes `role_model` so the handoff header names the model that will actually run.
**Correction to the notes below:** the account's real ids from `GET https://api.deepseek.com/models` are **`deepseek-flash`** and **`deepseek-v4-pro`**. `deepseek-v4-flash` and `deepseek-v4-flash-vision-exp` **do not exist**, so mandarin's `config.json` pin of `deepseek-v4-flash` is invalid (inert only because mandarin runs `agent-dispatch`). Mandarin's 7 registry roles carried `model: "deepseek"`, which is not an id and would 400 now that role models are live — corrected to `deepseek-flash`.
**Files:** `executor.py` (resolve role model), `graph.py _role_spec/_execute` (pass it) — as predicted.

### TD-5.4-2: Reasoning / thinking-effort passthrough

**Status:** Open
**Goal:** Optional reasoning-effort / thinking param on the chat call for reasoner-tier nodes; document which provider models honor it. Currently the `http` runner sends no effort control (`model_name` only).
**Why:** heavy verify/review nodes (code-reviewer, verify chains) may need deeper reasoning; measure vs cost on the epic-25 data.
**Files:** `executor.py` chat payload + config/env knob.

### TD-5.4-3: Mid-chain human gate (pause-after-link / approval mode)

**Status:** Open
**Goal:** Add `--chain <name> --auto --pause-after <link>` (and/or an approval mode) so the auto chain runner stops at a named link for human review (e.g., after `uiux-designer`) then resumes headless; honor `human_approval` gates in that mode instead of always auto-approving.
**Why:** Flow B (implement) needs "review the UI playbook before wiring logic" without losing headless automation for the rest of the chain. Today only `--json`/HTTP step-driving or IDE per-link (`@Governor v5`) can pause mid-chain; `chain.py` auto-approves by design.
**Files:** `chain.py` (runner + per-link gate), `cli.py` flag, `graph.py` review.

### TD-5.4-4: Per-repo eval cases (mandarin main battery)

**Status:** Open
**Goal:** The default eval battery's cases target `solar-v5-wire` files that do not exist on mandarin `main` (e.g. `apps/frontend/src/shared/utils/cn.ts`, epic-25 artifacts) — so eval is not a valid signal on main yet. Define a main-scoped battery (per-repo `--cases` file or parametrized defaults) once the real epic-25 lands.
**Files:** `eval.py` `DEFAULT_CASES` / per-repo cases file.

### TD-5.4-5: `uplink` wiring (hub knowledge uplink)

**Status:** Open
**Goal:** Implement `uplink: none | hub:<url>` beyond the stored config placeholder: push curated record (digests/run-cards/decisions) to an owned hub endpoint with graceful degradation; repo stays source of truth. Currently `uplink` exists only in `core.py` defaults + `Config` — no runtime module reads it.
**Why:** design intent (v5 §11); defer until a hub exists / the epic-25 data shows the need.
**Files:** core field (exists), new uplink module + ledger/runcard hooks.

### TD-5.4-6: `doctor` reports the resolved model

**Status:** Open
**Goal:** `doctor` should echo the model that will actually run (env `SOLAR_MODEL` → `cfg.model` → default `deepseek-chat` → concrete id) so a mis-set alias or env is caught before a run. The mandarin config now pins `model: "deepseek-v4-flash"` (concrete id, not the `deepseek-chat` alias, which can be re-pointed).
**Caution (2026-09-18):** the concrete id it pins, `deepseek-v4-flash`, **does not exist** — `GET https://api.deepseek.com/models` returns `deepseek-flash` and `deepseek-v4-pro` only. Mandarin's `.solar/config.json` is therefore invalid, and inert only because that repo runs `agent-dispatch`. Fix it before mandarin moves to `--runner http`. Note that v5.4.0 corrected the 7 registry roles to `deepseek-flash` and role `model` now beats `cfg.model`, so the registry fix already masks the bad config pin for those roles.
**Files:** `cli.py` doctor checks.

### TD-5.4-7: A command vocabulary per repo (mandarin has none)

**Status:** Open
**Goal:** Promyro now has `.solar/commands.json` (13 commands) and per-role `exec_allow`. **Mandarin has neither** — its role prompts name *activities* ("frontend-audit (Parts 1-4)", "design-audit", "codegraph"), not commands, so its vocabulary cannot be copied from Promyro and has to be derived from its own `package.json` scripts.
**Why:** until it exists, mandarin's exec-declaring roles (frontend-engineer, backend-engineer, docs-writer) carry the `exec` group but resolve to zero commands. `granted()` correctly returns none and the tool is simply absent — safe, but those roles cannot run their own checkers.
**Files:** mandarin `.solar/commands.json` (new) + `exec_allow` per role.

## v4 — Context Efficiency, Effort Simulation, Compaction

### TD-4-1: Instructional steering in agent bodies for direct invocations

**Status:** Deferred
**Problem:** When a user invokes a high-effort agent directly (e.g. `@Security Auditor`)
without going through the governor, no preamble is injected. Direct invocations
bypass the `effort_preamble_lookup` table entirely.

**Options:**

A) Add a reasoning directive to the body of each high-effort agent:

> "Reason step-by-step through all edge cases and failure modes before producing output."

Add brevity directive to each low-effort agent:

> "Be concise. Produce only what is explicitly requested. Skip optional analysis."

B) Leave as-is. Accept that direct invocations have no effort steering.

**Recommendation:** Option B — defer until TD-4-3 resolves; adding directives now
means rework when native `tiers:` lands.

**Trigger to act:** A low-effort agent (Docs Curator, Solar Bootstrap) produces
noticeably verbose output on direct `@` invocations.

**Files if Option A:** 6 high-effort agent bodies + 3 low-effort agent bodies.

---

### TD-4-2: ~~Workspace reasoning floor~~

**Status:** Resolved — 2026-04-05
`github.copilot.chat.responsesApiReasoningEffort` was added then removed.
Effort is controlled exclusively by the governor `effort_preamble_lookup` table.
No workspace floor exists.

---

### TD-4-3: Migrate to VS Code native `tiers:` when stable

**Status:** Deferred
**Trigger:** `tiers:` front matter (vscode issue #306717) marked stable in VS Code
release notes.

**Migration steps when ready:**

1. Add `tiers: [thorough]` to high-effort agent front matter; `tiers: [quick]` to low-effort agents.
2. Remove `effort_preamble_lookup` section from `orchestration-governor.agent.md`.
3. Remove discoverability comments from agent bodies (`<!-- effort: high ... -->`).
4. Update `effort-simulation.md` to document the migration.

**Note:** No `settings.json` entry to remove (already removed in TD-4-2).
Agent files carry no effort data — migration touches governor + 9 agent body comments only.

---

### TD-4-4: `ultrathink` keyword for Claude max-effort delegations

**Status:** Deferred — low priority
**Problem:** Claude models respond to `ultrathink` as a token-budget signal.
The `max` effort preamble does not currently include it.

**Option:** Append `ultrathink` to the injected preamble for `effort: max` calls
in `effort_preamble_lookup`. Document in `effort-simulation.md`.

**Trigger to act:** First agent assigned `max` effort level is introduced.

---

### TD-4-5: Audit `user-invocable` vs handoff-only agent classification

**Status:** Open
**Problem:** Currently several agents are marked `user-invocable: true` but may
only ever be reached via governor delegation or a `handoffs:` transition from
another agent. If an agent is never intended for direct `@` invocation, setting
`user-invocable: false` reduces surface area and prevents unintended direct calls
that bypass governor oversight.

**Questions to answer:**

- Which agents are legitimately user-facing vs. internal pipeline workers?
- Does VS Code's `handoffs:` frontmatter work regardless of `user-invocable`?
  (i.e. can a `user-invocable: false` agent still appear as a handoff target?)
- If so, flip all pipeline-internal agents to `user-invocable: false` and only
  expose entry-point agents (Governor, Design Architect, Explore) as `true`.

**Trigger to act:** Confirm VS Code handoff behavior with `user-invocable: false`
agents — one test call is sufficient to verify.

---

## v1 / v2 / v3 — Prior Version Items

> Add any carry-over items from v1–v3 audits here as `TD-1-x`, `TD-2-x`, `TD-3-x`.
