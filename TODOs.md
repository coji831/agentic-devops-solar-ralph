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

**Status:** Resolved 2026-09-18 — shipped in **v5.5.0**. Ladder `SOLAR_REASONING_EFFORT` > role `reasoning` > `cfg.reasoning_effort`, resolved by `executor.reasoning_effort()` and sent as `reasoning_effort` on the chat call. **Off by default**: nothing is sent unless a level supplies a value, so no existing repo changes behaviour. The value is deliberately **not** validated here — providers disagree about the scale and about whether they accept the field at all, so a wrong value has to come back as the provider's own error rather than being silently dropped. `doctor` echoes it when set. **Measured against DeepSeek 2026-09-19** — see the verification note below; it is accepted, so this is no longer a "confirm before relying on it" item.
**Goal:** Optional reasoning-effort / thinking param on the chat call for reasoner-tier nodes; document which provider models honor it. Currently the `http` runner sends no effort control (`model_name` only).
**Why:** heavy verify/review nodes (code-reviewer, verify chains) may need deeper reasoning; measure vs cost on the epic-25 data.
**Files:** `executor.py` chat payload + config/env knob.

**Verification (2026-09-19, v5.6.3):** exercised against the real provider for the first time. `SOLAR_REASONING_EFFORT=low` with `SOLAR_MODEL=deepseek-v4-pro` returned **exit 0, APPROVED, no error** (1479 in / 62 out, 1 tool call), against a no-effort baseline of 1685 / 154. So DeepSeek **accepts** the field on that model — the previous "no DeepSeek id documents it" caution was about documentation, and the API is more permissive than the docs. **Not overclaimed:** one value, one model, one sample; the 62-vs-154 output gap is consistent with the field taking effect, not proof. Still unmeasured: which scale the provider honours, and whether a rejected value errors or is ignored.

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
**Resolved (2026-09-19, v5.6.3):** both engagements pin valid ids — mandarin `deepseek-flash`, Promyro `deepseek-chat` — and `doctor` reports `model: PASS` for each. The blocker on moving mandarin to `--runner http` is gone.
**Files:** `cli.py` doctor checks.

### TD-5.4-7: ~~A command vocabulary per repo (mandarin has none)~~

**Status:** Resolved 2026-09-18 — shipped in **v5.5.0**. Mandarin's `.solar/commands.json` declares **20** commands derived from its own `package.json` (16 `check`: typecheck, lint, test, test*full, format_check, design_lint, design_audit, the five `check:*`sweeps, three`validate:_`content validators; 4`read`: git head/status/diff/log). `exec_allow`: frontend-engineer 12, backend-engineer 12, docs-writer 8 — **0 dangling grants**, verified by resolving every name against the loaded vocabulary. Destructive scripts are deliberately excluded: `format`, `format:all`, `cleanup:radical-content`, `logs:prune`, and `generate:system-map --emit`; only its `--check`form is reachable. Also fixed the config's non-existent`deepseek-v4-flash`pin (caught by the new doctor check).
**Goal:** Promyro now has`.solar/commands.json`(17 commands) and per-role`exec_allow`. **Mandarin has neither** — its role prompts name \_activities_ ("frontend-audit (Parts 1-4)", "design-audit", "codegraph"), not commands, so its vocabulary cannot be copied from Promyro and has to be derived from its own `package.json` scripts.
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

## v5.6 — Install consistency (opened 2026-09-19 by comparing two real engagements)

> Shipped: **v5.6.0** TD-5.6-1, 2 · **v5.6.1** TD-5.6-5 · **v5.6.2** TD-5.6-6, 7 · **v5.6.3** TD-5.6-9, 10 · **v5.6.4** TD-5.6-11, 12.
> Still open: TD-5.6-3, TD-5.6-4 (additions, neither can produce a wrong result), TD-5.6-8
> (cosmetic) and TD-5.6-13 (a leak that only bites a long-lived process).

### TD-5.6-1: ~~Portable config + refreshable install~~

**Status:** Resolved 2026-09-19 — shipped in **v5.6.0**. `Config.repo` is optional and `root` derives from the config file's own location; `to_dict` omits `repo` when empty and never persists runtime-only fields, so a saved config names nothing machine-specific. `init` now MERGES (existing wins, new keys added, output names what was kept/added) instead of overwriting `config.json` while skipping `registry.json` - the asymmetry nobody could re-run. `.solar/VERSION` records the installed runtime and `doctor` WARNs on drift. The `.gitignore` block is marker-delimited and rewritten in place, replacing a guard (`if ".solar/state" not in text`) that could neither revise a block nor tell a duplicate from a conflict. **Note:** this is the enabling fix, not the commit: the engagement repos' `.solar/` data is still uncommitted, and both carry pre-existing unrelated modifications, so staging it is the owner's call.
**Why it mattered:** the two engagements had _opposite_ rules for `.solar/config.json`, and the one that ignored it is the one where a non-existent model id sat unreviewed.

### TD-5.6-2: ~~Model ids duplicated across repos~~

**Status:** Resolved 2026-09-19 — shipped in **v5.6.0**. A model id could be written in five places (`executor.DEFAULT_MODEL`, `cfg.model`, a role's `model`, `SOLAR_MODEL`, `.agent.md` frontmatter), so a rename meant an edit per repo per file. `MODEL_TIERS` maps a tier to the concrete id per provider family and a repo declares `model_tier`; the ladder interleaves ids and tiers with an explicit id winning at the same level. An unresolvable tier sets `error` and REJECTS the run rather than falling back to a default. **Still true:** nothing validates that the tier's id is current - `doctor` reports it, and the provider's `/models` is the check.

### TD-5.6-3: The IDE model plane has no table either

**Status:** Open
**Goal:** `.agent.md` frontmatter pins the IDE plane with display names (`model: DeepSeek V4 Flash (deepseek)`) while the runtime needs API ids (`deepseek-flash`). v5.6.0 added a `doctor` guard that catches a display name transcribed into a runtime config, and a comment naming the two planes - but the IDE names are still hardcoded per repo per agent file, so there is nothing to rename centrally when the picker renames a model.
**Why:** this is the plane the phantom `deepseek-v4-flash` came from. Guarding the transcription is not the same as having one place to change.
**Files:** `solar-install-inventory.md` (agent frontmatter templates) + a documented mapping, or a generator.

### TD-5.6-4: `doctor` does not check MCP servers or the smoke task

**Status:** Open
**Goal:** §10 has described install verification as "MCP servers connect · model endpoints reachable · smoke task runs end-to-end on THIS repo" since v5. What `doctor` actually does is config, checkpoint, graph compile, registry, runner, model resolution + provider list, uplink validity and install version (§10 now says which). The MCP check and the end-to-end smoke task are still missing, so a repo can pass `doctor` and still fail its first dispatch.
**Files:** `cli.py` `cmd_doctor` + probably `server.py`/MCP config discovery.

### TD-5.6-5: ~~The ledger overwrote itself, destroying whatever else was there~~

**Status:** Resolved 2026-09-19 — shipped in **v5.6.1**. `ledger.render` built three sections from the current state and did a wholesale `write_text`, so the ledger was a view of the _last_ run and anything else at that path was destroyed. It destroyed a 115-line hand-written task brief in a real engagement when an unrelated integration run wrote over it. `ledger.record` now appends: one section per run keyed by thread, each wrapped in its own begin/end markers, so re-recording the same thread updates its OWN section and prose before/between/after sections is untouched. Nothing is ever deleted. `chain.py`/`cli.py`/`server.py` pass the thread; `runcard` carries `decisions` so the structured record stands alone. **Note:** this is why the install block's line about ledger.md is now accurate — it had described an accumulation the code did not perform.
**Files:** `ledger.py`, `cli.py` `_write_artifacts`, `chain.py`, `server.py`, `runcard.py`, `tests/test_ledger.py`.

### TD-5.6-6: ~~Reusing a thread id accumulates `work_queue` and `decisions_log`~~

**Status:** Resolved 2026-09-19 — shipped in **v5.6.2**. The accumulating channels
(`work_queue`, `decisions_log`, `tokens_in`, `tokens_out`, `tool_calls` are all
`operator.add`) no longer leak across runs: a start with **no pending interrupt** clears that
thread's own history before invoking, and a **resume** continues untouched. The rejected
alternative — an id per invocation — would have broken `run --json` followed by `--approve`,
which must resume the SAME thread; the scoping is safe because the CLI already refuses a
resume against a thread that is not paused and a start against one that is. The reset is
announced as the first entry of the fresh run's own decisions log, so it is visible in the
run-card and the ledger rather than silent. Measured on a scratch repo: `work_queue` **2 rows
/ 8 decision steps** before, **1 row / 5 steps** after; through the CLI twice on the default
thread, the ledger section for `t1` carries one `T1` row.
**Files:** `graph.py` (`run_step` + `_clear_thread`), `tests/test_thread_state.py`.
**Goal:** Both channels are `Annotated[list, operator.add]`, so a second `run` on the same thread inherits the first run's lists. The default thread is a fixed `t1`, which makes this the NORMAL path rather than an edge case: a second `solar-governor run "<task>"` with no `--thread` produces a work queue with two rows and a decisions log with the first run's entries still in it. Observed while proving the v5.6.1 ledger change (one section showing two `T1` rows and `material_gate -> READY` twice).
**Why:** the state a run reports is wrong, and it is wrong for anyone who ever runs more than one task without naming a thread. A fresh start needs either a per-invocation thread id or an explicit reset of the accumulating channels on a non-resume start - the constraint is that `run --json` followed by `--approve` must still resume the SAME thread, so the default cannot simply become random.
**Files:** `graph.py` `initial_state`/`run_task`, `cli.py` thread default, `core.py` channel annotations.

### TD-5.6-7: ~~`--runner stub` still calls the provider when a key is present~~

**Status:** Resolved 2026-09-19 — shipped in **v5.6.2**. `executor.run` takes the
already-resolved runner (`select_runner` is decided once, by the caller) and honours an
explicit `stub` before any provider config is read, so the offline runner is offline by
contract rather than by accident of a missing key. The stub also names its reason
(`runner=stub, by request` vs `no SOLAR_API_KEY set`), because a fallback and a choice are
different facts about a run and nothing else distinguished them. Measured with a live key and
a dead endpoint: `runner="http"` returns `deepseek-chat` + `Connection error.`;
`runner="stub"` returns `stub`, `0/0` tokens, no error; `run --runner stub --json` exits 0.
**Note:** `doctor`'s runner check is corrected too — a selected `http` with no key is now a
WARN, not a PASS describing calls that will not happen.
**Goal:** `executor.run` fell back to the stub on a missing KEY, not on the selected runner, so
`run --runner stub` with `SOLAR_API_KEY` set performed a real HTTP call. The README's runner
table says the stub is "Deterministic plan text (offline structure tests)", which is only true
while the key is unset — a mismatch that would surprise anyone reaching for `--runner stub`
precisely to stay offline, and it spends tokens when the intent was not to.
**Files:** `executor.py` (`run`, `stub_result`), `graph.py` `_execute`, `cli.py` `cmd_doctor`,
`solar-governor/README.md` (the runner table).

### TD-5.6-8: Writers emit CRLF on Windows, so install bytes are platform-dependent

**Status:** Open — cosmetic at present, measured 2026-09-19 during the v5.6.2 engagement
refresh. **Severity: low.**
**Goal:** `install.write_version` (and the other `Path.write_text` writers — `cmd_init`'s
config, the ledger section) translate `\n` to the platform separator, so `.solar/VERSION`
lands as `5.6.2**\r\n**` and `config.json` as 10 CRLF lines. Git says so on every refresh:
`warning: in the working copy of '.solar/VERSION', CRLF will be replaced by LF`.
**Measured, so as not to overstate it:** both engagements are `core.autocrlf=true`, so git
normalises on add and **no churn occurs** — `git status` is clean after the refresh commit,
and the warning is the whole symptom today. It becomes real on an `autocrlf=false` repo or a
Linux clone: `init` then writes LF, so the committed bytes depend on the machine that last
ran `init`, and a Windows→Linux refresh shows a one-line diff. That undercuts the property
v5.6.0 was built for — a refresh is a no-op when nothing changed.
**Files:** `install.py` (`write_version`, and the block writer if it shares the pattern),
`cli.py` `cmd_init`. Fix shape: pass `newline="\n"` to the text writers.

### TD-5.6-9: ~~`--json` and `serve` crashed on a fresh clone~~

**Status:** Resolved 2026-09-19 — shipped in **v5.6.3**. `run_step` created the checkpoint
directory; `pending_interrupt` opened the same database without creating it. A repo with
`.solar/config.json` but no `.solar/state/` therefore died with a bare
`sqlite3.OperationalError: unable to open database file` and **exit 1** — a code outside the
documented `0/2/10/11/12` — while the interactive path on the same repo worked, because it
happened to mkdir first. Two paths disagreeing about one repo is the defect. The state is not
exotic: `state/` is gitignored while the config and registry are tracked, so it is what a
FRESH CLONE looks like. Both paths now share `graph._ensure_checkpoint_dir`. Found by running
the live HTTP verification, not by reading.
**Related, same release:** an unreadable `config.json` also escaped as a traceback and exit 1;
it is a usage/state error, so `cmd_run` now prints the reason and the path and exits **2**.
`doctor`'s `checkpoint-writable` tested whether `state/` EXISTS, so it reported FAIL for a
clone that runs fine — it now tests whether the directory can be CREATED, and names it.
**Files:** `graph.py` (`_ensure_checkpoint_dir`), `cli.py` (`cmd_run`, `cmd_doctor`),
`tests/test_install_paths.py`.

### TD-5.6-10: ~~A UTF-8 BOM killed every command~~

**Status:** Resolved 2026-09-19 — shipped in **v5.6.3**. `json.loads` rejects a leading BOM,
and a BOM is an ordinary outcome of editing a `.solar/` file on Windows — PowerShell 5.1's
`Set-Content -Encoding utf8` writes one, as does Notepad's "UTF-8 with BOM". Every command died
with a traceback and exit 1; `doctor` at least named it (`config: FAIL - Unexpected UTF-8
BOM`). Swept rather than patched: `core.read_text`/`read_json` read as `utf-8-sig` (a no-op
without a BOM) and are now used by every reader of a human-authored file — `config.json`,
`registry.json`, `commands.json`, `.solar/VERSION` (a BOM made the marker compare as
`\ufeff5.6.2` and report drift against itself), `eval-cases.json`, the explicit `--cases` path,
and `resolve_result` (an agent-written `.result.md` leaked its BOM into the specialist output).
**Deliberately excluded:** `ledger.md` — reading as `utf-8-sig` and writing back as `utf-8`
would strip content the runtime did not write, which §23 forbids. Also excluded: `.gitignore`
(a BOM there neither crashes nor changes behaviour) and repo files read by the workspace tools.
**Files:** `core.py` (the helpers), `registry.py`, `install.py`, `commands.py`, `eval.py`,
`executor.py` `resolve_result`, `cli.py`, `tests/test_install_paths.py`.

### TD-5.6-11: ~~A local, keyless endpoint was unreachable~~

**Status:** Resolved 2026-09-19 — shipped in **v5.6.4**. `executor.run` fell back to the stub when
`api_key()` was `None`, whether or not the runner had been chosen explicitly, so `run --runner http`
against a healthy local endpoint sent **no request at all** and reported `tokens 0/0`, APPROVED — a
run that never happened reading as a success. An explicit `http` run now sends `sk-no-key-required`
(the value llama.cpp's docs pass; Ollama's say "required but ignored"), so the placeholder is
recognised in a server log rather than looking like a leaked secret. Auto still resolves to the stub
without a key. **Measured on the same mock-local probe: 0 endpoint calls / `model=stub` / 0/0 → 2
calls / `deepseek-chat` / 250/30 / APPROVED.** `doctor`'s runner check was corrected with it: a
keyless `http` is no longer WARNed as broken, and its model probe now lists a keyless endpoint and
WARNs when one does not answer (`cannot list its models`).
**Files:** `executor.py` (`resolved_key`, `known_models`), `cli.py` (`cmd_doctor`, `_model_check`),
`tests/test_local_endpoint.py`.

### TD-5.6-12: ~~`tokens: 0/0` meant two different things~~

**Status:** Resolved 2026-09-19 — shipped in **v5.6.4**. An endpoint may omit the usage block, so a
real call to a real model could be recorded with the same two numbers a stub produces, and the token
column — the thing a local-vs-cloud comparison measures — could be silently empty. `ExecutorResult`
carries `usage_reported`, the run-card records `tokens.reported`, and the state/`--json` contract
carry it too. Related and in the same release: the card now records **`provider`** (endpoint
host:port, or `stub`), because a model id cannot carry provenance — `qwen3:8b` on a laptop and a
hosted `qwen3:8b` are the same string.
**Files:** `executor.py`, `core.py` (`SolarState`), `graph.py` `_execute`, `runcard.py`,
`ledger.py` (footer), `cli.py` (`_state_summary`, `--json`).

### TD-5.6-13: `run --runner X` leaks `SOLAR_RUNNER` into the process environment

**Status:** Open — **severity: low**, found 2026-09-19 while testing v5.6.4.
**Goal:** `cli.cmd_run` implements `--runner` by setting `os.environ["SOLAR_RUNNER"]` and never
restoring it. In a one-shot CLI process that is exactly right (and the flag/knob cannot disagree).
In a long-lived process — `serve`, a wrapper calling `main()` twice, or a test suite — the first
`--runner stub` silently becomes the runner for everything that follows, and env beats config **by
design**.
**Measured, so as not to overstate it:** it made `tests/test_local_endpoint.py` pass alone (6/6) and
fail in the full suite with `model == 'stub'`, because an earlier module had run one. Fixed on the
test side with a hermetic env fixture; the product-side leak is what remains.
**Files:** `cli.py` `cmd_run` — and the contract question first: `--runner` could be threaded
through `select_runner` as a parameter instead of via the environment.

## v5.7 — Local hosted models + a provider registry (opened 2026-09-19)

> Shipped: **v5.7.0** TD-5.7-1 (the `providers` + `models` registry).

### TD-5.7-1: ~~A `providers` + `models` config, so a model is an alias not an env var~~

**Status:** Resolved 2026-09-19 — shipped in **v5.7.0**. What is built: a shipped `providers`
table (17 entries, each `base_url` probed unauthenticated before shipping — two candidates that
"everybody knows" were dropped by that check), a repo-declared `models` map whose aliases win at
every rung of the existing ladder, `headers` + `extra_body` per provider/alias so a router's own
fields work, per-role `provider`, and a `provider` check in `doctor` that names the provider, the
endpoint and whether the credential env var is set. Verified live on DeepSeek: `provider=deepseek`,
`model=fast -> deepseek-flash`, exit 0, APPROVED, `tokens 699/139 reported: true`.
**Two things the tests caught that reading would not:** router fields cannot be keyword arguments
(the SDK rejects unknown keywords and NO request leaves the process — they ride in `extra_body=`,
with the runner's own keys stripped first), and `resolve_tier`'s `family or provider_family()`
fallback re-inferred from the environment, so a declared LOCAL provider resolved `fast` to a
**DeepSeek id**. Both are fixed and tested.
**Left open on purpose:** no `--provider` flag (it would repeat the `SOLAR_RUNNER` process leak,
TD-5.6-13 — switching is `SOLAR_MODEL=<alias>`); and Azure OpenAI / Bedrock / Vertex are absent
because Azure needs its own client + `api-version` and the others are not OpenAI-compatible
without a gateway — an entry that cannot work is worse than no entry.
**Still open from the same design:** whether SOLAR should own cross-provider routing/fallbacks or
delegate them to a gateway (LiteLLM self-hosted, or OpenRouter hosted). Today it delegates: an
alias can point at a gateway URL, and the gateway owns fallbacks, `context_window_fallbacks` and
per-model spend. Revisit if the runtime needs to route per role without a gateway running.
**The measured facts that shaped it, kept as the record:**
**Goal:** today a repo has one provider and one model, chosen by a ladder over `SOLAR_BASE_URL` /
`SOLAR_MODEL` / `SOLAR_API_KEY` (env-only, never persisted) and `cfg.model` / `cfg.model_tier`.
There is no way to say "`local-qwen` is `qwen3:8b` on localhost, `reasoner` is `deepseek-v4-pro`
in the cloud, and this role uses the first while that chain uses the second".
**Measured 2026-09-19:** the config **plumbing already tolerates the block** — `install.read_config`
reads it and `init`'s merge preserves it byte-identically — while `Config.load` silently drops it,
because there is no such dataclass field. So the work is a runtime change, not a schema migration:
no hand-written config is at risk.
**Constraint (non-negotiable):** `.solar/config.json` is **committed** in both engagements, so a
provider entry carries `api_key_env: "SOLAR_API_KEY"` — a **name**, never a value. That is LiteLLM's
documented `api_key: os.environ/VAR` indirection, and skipping it invites a key into a tracked file.
A provider with an empty `api_key_env` is the local case, and depends on v5.6.4's placeholder.
**Fact-checked against the current vendor docs (OpenRouter, vLLM, llama.cpp, Ollama, LM Studio):**
`{base_url, api_key_env, family}` is **not** enough. A provider also needs `headers: {}` (OpenRouter
attribution headers, provider betas) and a model needs `extra_body: {}` (OpenRouter's `provider`
routing object, its `models` fallback list, `route: "fallback"` — all body-level). And a model id
must stay **opaque**: `anthropic/claude-sonnet-4.5`, `:nitro`/`:floor` variants, `~` latest aliases,
and llama.cpp's `/v1/models` id which is a **file path** unless `--alias` is set. Never parse it.
**Shape:** shipped defaults merged with repo overrides (the `registry.load` pattern, so aliases are
not re-declared per repo — the duplication v5.6.0 removed); `resolve_model` gains one alias rung, in
that one place; `base_url()`/`api_key()` stop being env-only globals; a declared `family` per
provider also fixes the local tier gap (`provider_family()` infers from the host, so any local
endpoint currently RAISES as soon as a repo declares a `model_tier`).
**Composes with:** a self-hosted gateway (LiteLLM) or a hosted one (OpenRouter) — aliases can point
at a gateway URL, which is where fallbacks, `context_window_fallbacks` and per-model spend already
live. Decide whether SOLAR should own that routing or delegate it before building this.
**Files:** `core.py` (field + merge), `executor.py` (resolution + provider-derived base_url/key),
`cli.py` (doctor reports provider/base_url; `--json` carries it), `runcard.py`, docs, tests.

### TD-5.7-2: Cross-provider fallback — does SOLAR own routing, or does a gateway?

**Status:** Deferred (decided 2026-09-19, v5.7.1 — deliberately not built)
**Goal:** Decide whether the runtime re-routes a failing provider mid-run (model A at provider X →
model B at provider Y), or keeps delegating that to a gateway.
**Why deferred:** the gateway already owns this and owns it better — an alias may point at a
LiteLLM URL or use OpenRouter's own `provider` routing object in `extra_body`, and per-model spend
and `context_window_fallbacks` live there too. Building a second, weaker router inside a graph
node would duplicate policy that a gateway can enforce with real usage data. Worth revisiting only
for driving a role with **no gateway running** (a laptop with a local model and one cloud key).
**Decision needed first:** which failures are routable (connection refused? 5xx? a 429 with a
retry-after? a 404 for a model id that no longer exists?) and whether a fallback must be recorded
in the run-card as a separate fact, since "which provider answered" would no longer be a single
value per node.
**Files:** `executor.py` (`_tool_loop` retry path), `runcard.py` (route provenance), docs, tests.

### TD-5.7-3: The handoff header names the alias, not the resolved id

**Status:** Open (found 2026-09-19 while verifying v5.7.1)
**Goal:** `write_handoff` prints `_model routing: {model}_` from `model_name(cfg_model, role_model)`,
which resolves through `resolve_target` **without** the provider tables — so a role declaring an
alias (`model: local-qwen`) makes the handoff say `local-qwen` where the runtime would call
`qwen3:8b` at a declared provider.
**Why it matters (and why it is small):** the handoff describes the **IDE plane**, which pins its
own models in `.agent.md` frontmatter (TD-5.6-3), so nothing downstream is actually wrong — but the
header is a model claim about a run, and this workspace's rule is that a report must not read as
something it isn't. The fix is to pass the resolved target (or its model + provider) into
`write_handoff` from `graph._dispatch_agent`, which already has `cfg` and the role spec.
**Files:** `executor.write_handoff` signature, `graph._dispatch_agent` call site, the handoff test.

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
