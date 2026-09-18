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

## v5.4.x — Backlog (opened after v5.3.1 from the real epic-25 pilot on mandarin main. Shipped: v5.4.0 TD-5.4-1 · v5.4.1 TD-5.4-8 · v5.4.2 TD-5.4-9 · v5.5.0 TD-5.4-2, 4, 5, 6, 7, 10. Still open: TD-5.4-3 only.)

### TD-5.4-1: ~~Per-node model routing~~

**Status:** Resolved 2026-09-18 — shipped in **v5.4.0**. Resolution is `SOLAR_MODEL` env → role `model` → `cfg.model` → default; an empty value at any level is skipped, so a registry that leaves `model` as `""` keeps inheriting exactly as before. `graph._role_spec` was returning `(role, system)` only and dropping every other key, so no role spec could reach the executor at all — it now returns the full dict, with a `_role_prompt` helper and both call sites updated. `write_handoff` also takes `role_model` so the handoff header names the model that will actually run.
**Correction to the notes below:** the account's real ids from `GET https://api.deepseek.com/models` are **`deepseek-flash`** and **`deepseek-v4-pro`**. `deepseek-v4-flash` and `deepseek-v4-flash-vision-exp` **do not exist**, so mandarin's `config.json` pin of `deepseek-v4-flash` is invalid (inert only because mandarin runs `agent-dispatch`). Mandarin's 7 registry roles carried `model: "deepseek"`, which is not an id and would 400 now that role models are live — corrected to `deepseek-flash`.
**Files:** `executor.py` (resolve role model), `graph.py _role_spec/_execute` (pass it) — as predicted.

### TD-5.4-2: ~~Reasoning / thinking-effort passthrough~~

**Status:** Resolved 2026-09-18 — shipped in **v5.5.0**. Ladder `SOLAR_REASONING_EFFORT` > role `reasoning` > `cfg.reasoning_effort`, resolved by `executor.reasoning_effort()` and sent as `reasoning_effort` on the chat call. **Off by default**: nothing is sent unless a level supplies a value, so no existing repo changes behaviour. The value is deliberately **not** validated here — providers disagree about the scale and about whether they accept the field at all, so a wrong value has to come back as the provider's own error rather than being silently dropped. `doctor` echoes it when set. **Still unmeasured against DeepSeek**: no DeepSeek id documents `reasoning_effort`, so treat it as provider pass-through and confirm before relying on it.
**Goal:** Optional reasoning-effort / thinking param on the chat call for reasoner-tier nodes; document which provider models honor it. Currently the `http` runner sends no effort control (`model_name` only).
**Why:** heavy verify/review nodes (code-reviewer, verify chains) may need deeper reasoning; measure vs cost on the epic-25 data.
**Files:** `executor.py` chat payload + config/env knob.

### TD-5.4-3: Mid-chain human gate (pause-after-link / approval mode)

**Status:** Open
**Goal:** Add `--chain <name> --auto --pause-after <link>` (and/or an approval mode) so the auto chain runner stops at a named link for human review (e.g., after `uiux-designer`) then resumes headless; honor `human_approval` gates in that mode instead of always auto-approving.
**Why:** Flow B (implement) needs "review the UI playbook before wiring logic" without losing headless automation for the rest of the chain. Today only `--json`/HTTP step-driving or IDE per-link (`@Governor v5`) can pause mid-chain; `chain.py` auto-approves by design.
**Files:** `chain.py` (runner + per-link gate), `cli.py` flag, `graph.py` review.

### TD-5.4-4: Per-repo eval cases (mandarin main battery)

**Status:** Resolved 2026-09-18 (mechanism) — shipped in **v5.5.0**. Resolution order is `--cases <file>` > `<repo>/.solar/eval-cases.json` > the built-in battery, via `eval.load_cases`. The important half is the honesty: when the built-ins are used on a repo that does not contain the pilot's files, `eval.battery_warning` prints a loud warning **before** the numbers and the aggregate carries `cases_source`, so a 0% can no longer be mistaken for "the harness is broken". **The mandarin `main` battery itself is still not authored** — that needs ground truth from `main`, which is a different branch; the gap is now visible instead of silently wrong.
**Goal:** The default eval battery's cases target `solar-v5-wire` files that do not exist on mandarin `main` (e.g. `apps/frontend/src/shared/utils/cn.ts`, epic-25 artifacts) — so eval is not a valid signal on main yet. Define a main-scoped battery (per-repo `--cases` file or parametrized defaults) once the real epic-25 lands.
**Files:** `eval.py` `DEFAULT_CASES` / per-repo cases file.

### TD-5.4-5: ~~`uplink` wiring (hub knowledge uplink)~~

**Status:** Resolved 2026-09-18 — shipped in **v5.5.0**. New `solar_governor/uplink.py`: `endpoint()` validates `none | hub:<http(s) url>`, `digest()` builds the curated record, `push()` posts it, and `status()` gives `doctor` a config-only verdict. Two properties are structural rather than promised: **push-only** (no download path exists in the module, so a hub cannot inject into a repo's context) and **never raises** (unreachable/refused/HTTP-error all return a status line, so a hub cannot fail or block a run). The digests carry `output_chars`, never the output, and truncate `objective`/`error` and the decisions list. Hooked into `cli._write_artifacts`, so it runs on the finished record. **No hub endpoint has consumed one yet.**
**Goal:** Implement `uplink: none | hub:<url>` beyond the stored config placeholder: push curated record (digests/run-cards/decisions) to an owned hub endpoint with graceful degradation; repo stays source of truth. Currently `uplink` exists only in `core.py` defaults + `Config` — no runtime module reads it.
**Why:** design intent (v5 §11); defer until a hub exists / the epic-25 data shows the need.
**Files:** core field (exists), new uplink module + ledger/runcard hooks.

### TD-5.4-6: ~~`doctor` reports the resolved model~~

**Status:** Resolved 2026-09-18 — shipped in **v5.5.0**. `cli._model_check` reports `<id> (from env SOLAR_MODEL | role | config | default)`, names the roles whose own `model` overrides the config (they can hide a stale pin), echoes `reasoning_effort` when set, and — with a key present — asks the provider for its model list, reporting **WARN** when the resolved id is neither served nor a known unlisted alias. Provenance comes from `executor.resolve_model`, now the one and only model ladder. `doctor` also gained a real WARN state (documented in §10, previously unreachable in code); only FAIL sets a non-zero exit.
**Goal:** `doctor` should echo the model that will actually run (env `SOLAR_MODEL` → `cfg.model` → default `deepseek-chat` → concrete id) so a mis-set alias or env is caught before a run. The mandarin config now pins `model: "deepseek-v4-flash"` (concrete id, not the `deepseek-chat` alias, which can be re-pointed).
**Caution (2026-09-18):** the concrete id it pins, `deepseek-v4-flash`, **does not exist** — `GET https://api.deepseek.com/models` returns `deepseek-flash` and `deepseek-v4-pro` only. Mandarin's `.solar/config.json` is therefore invalid, and inert only because that repo runs `agent-dispatch`. Fix it before mandarin moves to `--runner http`. Note that v5.4.0 corrected the 7 registry roles to `deepseek-flash` and role `model` now beats `cfg.model`, so the registry fix already masks the bad config pin for those roles.
**Files:** `cli.py` doctor checks.

### TD-5.4-7: ~~A command vocabulary per repo (mandarin has none)~~

**Status:** Resolved 2026-09-18 — shipped in **v5.5.0**. Mandarin's `.solar/commands.json` declares **20** commands derived from its own `package.json` (16 `check`: typecheck, lint, test, test_full, format_check, design_lint, design_audit, the five `check:*` sweeps, three `validate:*` content validators; 4 `read`: git head/status/diff/log). `exec_allow`: frontend-engineer 12, backend-engineer 12, docs-writer 8 — **0 dangling grants**, verified by resolving every name against the loaded vocabulary. Destructive scripts are deliberately excluded: `format`, `format:all`, `cleanup:radical-content`, `logs:prune`, and `generate:system-map --emit`; only its `--check` form is reachable. Also fixed the config's non-existent `deepseek-v4-flash` pin (caught by the new doctor check).
**Goal:** Promyro now has `.solar/commands.json` (17 commands) and per-role `exec_allow`. **Mandarin has neither** — its role prompts name _activities_ ("frontend-audit (Parts 1-4)", "design-audit", "codegraph"), not commands, so its vocabulary cannot be copied from Promyro and has to be derived from its own `package.json` scripts.
**Why:** until it exists, mandarin's exec-declaring roles (frontend-engineer, backend-engineer, docs-writer) carry the `exec` group but resolve to zero commands. `granted()` correctly returns none and the tool is simply absent — safe, but those roles cannot run their own checkers.
**Files:** mandarin `.solar/commands.json` (new) + `exec_allow` per role.

### TD-5.4-8: ~~Specialist tool loop has no termination rule~~

**Status:** Resolved 2026-09-18 — shipped in **v5.4.1**. The loop was `for _ in range(max_rounds): call; if tool_calls: continue`, with no termination pressure and no `temperature`, and it discarded `msg.content` whenever a tool call was present. Measured on a real read-only `investigator` link: no answer in 4 runs out of 5 over a one-file one-fact objective, up to 168k prompt tokens per failure, and the _identical_ command converged on the fifth. Resolution is three rules in `executor._tool_loop`: an explicit temperature (default 0.2), a budget notice once `NUDGE_ROUNDS_LEFT` rounds remain, and a final round called **with no tools offered** so it must return text. `forced_final` now travels to the run-card. This also corrects `docs/tuning.md` finding 3, which had blamed the objective; see `docs/versions/v5.md` §20.
**Files:** `executor.py` (`_tool_loop`, `temperature`, `_budget_notice`, `FINAL_ROUND_INSTRUCTION`), `core.py`/`graph.py`/`runcard.py`/`cli.py` (`forced_final`), `tests/test_executor.py` (12 cases).

### TD-5.4-9: ~~Runner selection cannot be overridden per run~~

**Status:** Resolved 2026-09-18 — shipped in **v5.4.2**. `select_runner` was `cfg_runner or os.environ.get("SOLAR_RUNNER", "")`, so a repo whose `config.json` set `runner` **always won and `SOLAR_RUNNER` was dead** — the opposite of `SOLAR_MODEL`, where env beats role and config. The ladder is now `SOLAR_RUNNER` > config > auto, and `run --runner {agent-dispatch,http,stub}` is a typed front door for it: the flag sets `SOLAR_RUNNER` for the process instead of writing `config.json`, so the flag and the knob cannot disagree and the committed config is never touched. An unrecognised value now **raises** instead of silently falling through to auto (`runner: "https"` used to pick a different runner with no signal); `doctor` reports it as `FAIL runner` and `/health` returns `runner: "invalid"` plus `runner_error` rather than 500-ing. Acceptance test: `--runner http` against Promyro (config pins `agent-dispatch`) — 8 calls, 26,848 tokens, APPROVED, and `config.json` read `agent-dispatch` before **and** after.
**Goal:** Let one run choose its runner without editing the repo's config. `select_runner` is `cfg_runner or os.environ.get("SOLAR_RUNNER", "")`, so a repo whose `config.json` sets `runner` **always wins and `SOLAR_RUNNER` is dead** — the opposite of `SOLAR_MODEL`, where env beats role and config. Add `--runner {http,agent-dispatch,stub}` to `run` (and/or make env win) so testing the `http` path on a repo configured for `agent-dispatch` does not require mutating a live engagement's config.
**Why:** found while running the v5.4.1 integration test — forcing `http` on Promyro meant editing `Promyro/.solar/config.json` and restoring it afterwards, on a repo whose `human_approval` and role grants are live. The docstring ("explicit config/env > auto") reads as if config and env are peers; the code makes config dominate.
**Files:** `executor.select_runner` (precedence), `cli.py` (`run` flag).

### TD-5.4-10: ~~A `REJECTED` run exits `0`~~

**Status:** Resolved 2026-09-18 — shipped in **v5.5.0**. Added `EXIT_REJECTED = 12` and `cli._exit_for(state)`: a completed step whose verdict is `REJECTED` exits 12 instead of 0, on both the `--json` and one-shot paths, and `--help` documents it. The alternative in the original note — leave the code alone and document that the verdict must be read from the JSON — was rejected: the exit code is a machine contract, and "the graph finished" is not the same claim as "the work was accepted". Observed live on all four `max_rounds` failures from the v5.4.1 integration test.
**Goal:** Decide the exit contract for a completed-but-rejected run. `--json` documents `0 complete · 10 agent-dispatch · 11 review · 2 error`, and a run whose verdict is `REJECTED` (executor error) currently exits `0` — so a wrapper driving on exit codes reads a hard failure as success. Observed on all four `max_rounds` failures in the v5.4.1 integration test, and on the v5.4.0 release surface. Either add a distinct code (e.g. `12 rejected`) or state plainly in `--help` that `0` means "the graph completed" and the verdict must be read from the JSON.
**Why:** the harness's whole premise is that a failure must not read as a success; the exit code is the one surface where it still does.
**Files:** `cli.py` (`_cmd_run_json` exit mapping), `README.md` / `docs/versions/v5.md` §9.

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
