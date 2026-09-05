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
