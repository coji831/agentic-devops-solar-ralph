# CHANGELOG

All notable changes to the SOLAR-Ralph framework are documented here.
Format: newest version first. Each entry covers what changed from the previous version and why.

---

<!-- RELEASE CHECKLIST (run before each release):
  1. Re-verify tool-set names in all template `*.agent.md` `tools:` frontmatter against VS Code Copilot docs:
     https://code.visualstudio.com/docs/copilot/customization/custom-agents
     Update if any name changed between VS Code releases.
  2. Re-verify hook field names against: https://code.visualstudio.com/docs/copilot/customization/hooks
  3. Bump the version in the three code files (`solar-governor/pyproject.toml`,
     `solar_governor/__init__.py` — `server.py` imports it) + `docs/versions/v5.md`.
     NOTE 2026-09-18: this item used to name `solar-install.prompt.md`. That file carries
     no version string, so the step could never have been carried out.
-->

---

## v5.6.3 — Released (2026-09-19) — the install path, verified against a live provider

**Theme:** verifying the HTTP runner against the real provider found two defects **on the
path to** it. Neither is about the runner's logic; both are about a repo that is perfectly
valid being unable to run, and failing in a way that does not read as itself.

### Fixed

- **TD-5.6-9 — `--json` (and `serve`) crashed on a fresh clone.** `run_step` created the
  checkpoint directory; `pending_interrupt` opened the same database **without creating it**.
  A repo with `.solar/config.json` but no `.solar/state/` — which is exactly what a clone
  looks like, since `state/` is gitignored while the config is tracked — died with a bare
  `sqlite3.OperationalError: unable to open database file` and **exit 1**, while the
  interactive path on the SAME repo worked because it happened to mkdir first. Two paths
disagreeing about one repo is the defect. Both now share `graph._ensure_checkpoint_dir`.
- **An unreadable config exited 1.** `cmd_run` let `Config.load`'s error escape as a raw
  traceback and exit 1 — outside the documented `0/2/10/11/12` that every wrapper in this
  repo drives on. It is a usage/state error, so it now prints the reason and the path and
  exits **2**.
- **TD-5.6-10 — a UTF-8 BOM killed every command.** `json.loads` rejects a leading BOM, and a
  BOM is an ordinary outcome of editing a `.solar/` file on Windows: PowerShell 5.1's
  `Set-Content -Encoding utf8` writes one, and so does Notepad's "UTF-8 with BOM". Swept
  rather than patched: `core.read_text`/`core.read_json` (read as `utf-8-sig`, a no-op on a
  file without a BOM) are now used by **every reader of a human-authored file** —
  `config.json`, `registry.json`, `commands.json`, `.solar/VERSION`, `eval-cases.json`, the
  explicit `--cases` path, and `resolve_result` (an agent-written `.result.md` used to leak
  its BOM into the specialist output). `ledger.md` is deliberately NOT included: reading it
  as `utf-8-sig` and writing back as `utf-8` would strip content it did not write, which
  §23 forbids.
- **`doctor` called a working repo broken.** `checkpoint-writable` tested whether `.solar/state/`
  **exists**, so it reported FAIL for a fresh clone that runs fine. It now tests whether the
  directory can be **created**, and names it.

### Measured — the live HTTP verification this came out of

The key was available only as a Windows **User** env var, invisible to `run` until the shell
sets it; every earlier "live" check was therefore really a stub-side check. With it set,
against `api.deepseek.com`:

| run | model | tokens in/out | tools | verdict | `forced_final` |
| --- | --- | --- | --- | --- | --- |
| plain | `deepseek-chat` | 1462 / 69 | 1 | APPROVED | False |
| reasoner baseline | `deepseek-v4-pro` | 1685 / 154 | 1 | APPROVED | False |
| `SOLAR_REASONING_EFFORT=low` | `deepseek-v4-pro` | 1479 / 62 | 1 | APPROVED | False |

- **TD-5.4-2's caveat is closed**, substantially: DeepSeek **accepts** `low` on
  `deepseek-v4-pro` — no error, APPROVED. Still not overclaimed: one value, one model, one
  sample. The 62-vs-154 output-token gap is *consistent with* the field taking effect, not
  proof of it.
- **TD-5.4-8 (tool loop) is confirmed live**: 3/3 terminated naturally, `forced_final` False.
- **The invalid-pin blocker is gone.** TD-5.6-2's caution said mandarin's `deepseek-v4-flash`
  had to be fixed "before mandarin moves to `--runner http`": mandarin now pins
  `deepseek-flash` and Promyro `deepseek-chat`, both valid, both `model: PASS`.
- **No path bypasses the selected runner** — audited every stub/key decision (only `run`'s
  guard and `select_runner`'s auto), and `eval`/`bench` execute through `graph.run_task`, so
  the guard covers them. Three dead-endpoint runs returned `Connection error.` → **REJECTED,
  exit 12**: an executor failure still does not read as success.

### Docs

- `docs/install-mandarin-main.md` told an operator to hand-edit `config.json` to switch to
  `http` — "the config runner wins over env, so edit the one field … flip back. (Do not
  commit config.json.)". Both claims died in v5.4.2 (env and `--runner` win) and v5.6.0 (the
  config is portable and committed), and it asked for exactly the kind of edit to a live
  engagement the flag exists to avoid. Rewritten, with the doctor expectations updated from
  `7 specialists` to `10 dispatchable (7 declared + 3 built-in)`.

### Not fixed here

- **TD-5.4-4** (mandarin `main`'s per-repo eval battery is still unauthored — now unblocked,
  since a key is available), **TD-5.6-4** (`doctor` still has no end-to-end smoke task; both
  defects above are instances of what it would have caught), **TD-5.6-3** (the IDE model
  plane has no table), **TD-5.6-8** (CRLF writers), and **`eval`/`bench` take no `--runner`
  flag**, so they need `SOLAR_RUNNER` in the environment — the same knob, differently reached.

## v5.6.2 — Released (2026-09-19) — the two silent wrong answers

**Theme:** the two defects v5.6.1 found and *recorded* instead of fixing. Both produced
output that looked right, which is exactly why neither was visible by reading.

### Fixed

- **TD-5.6-6 — a re-used thread inherited the previous run's state.** `work_queue`,
  `decisions_log`, `tokens_in`, `tokens_out` and `tool_calls` are `operator.add` channels,
  so an invoke over an existing checkpoint **appends** to the previous run's values instead
  of replacing them. The default thread is a fixed `t1`, which made the polluted state the
  _normal_ path: a second `run "<task>"` reported the first run's work row, its decisions and
  its token totals as if they were its own. A start with **no pending interrupt** now clears
  that thread's own history first, and a **resume** continues and clears nothing. The two
  cannot be confused — the CLI already refuses to resume a thread that is not paused, and
  refuses to start one that is. The reset is announced in the fresh run's own decisions log,
  so the run-card and the ledger explain why their totals start at zero.
- **TD-5.6-7 — `--runner stub` did not stub while a key was set.** `executor.run` chose the
  stub on a missing **key**, not on the selected **runner**, so `run --runner stub` with
  `SOLAR_API_KEY` in the environment made a real, billable HTTP call — the exact opposite of
  what reaching for the offline runner is for. `executor.run` now takes the already-resolved
  runner and honours an explicit `stub` before touching provider config.
- The stub now **names which reason produced it** — `runner=stub, by request` or
  `no SOLAR_API_KEY set`. A fallback and a deliberate choice are different facts about a run,
  and nothing else distinguished them.

### Changed

- `doctor`'s `registry` check said "10 specialists" for a repo that declares 7. The count
  was the **merged** set (`load` merges the built-in specialists under the repo's), so the
  number was right and the word was missing. It now reads
  `10 dispatchable (7 declared + 3 built-in)`, and shows no arithmetic when the two agree.
- `doctor`'s `runner` check described `stub` as "no API key -> deterministic stub" and
  returned **PASS for a selected `http` with no key** — a report of a run that will not
  happen as described. The wording is corrected, and the second case is now a **WARN**.
- `registry.declared()` reads the repo's OWN file before the built-ins are merged, so both
  numbers come from evidence rather than from arithmetic on the union.

### Measured

- **The thread reset, before and after, in one process on one scratch repo:** the same two
  tasks on the same thread give `work_queue` **2 rows / 8 decision steps** without the guard
  and **1 row / 5 steps** with it. Through the CLI twice on the default thread, the ledger's
  section for `t1` carries **one** `T1` row, with the reset note as its first decision.
- **The stub, with a live key and an endpoint nothing listens on:** `runner="http"` returns
  `deepseek-chat` with `Connection error.`; `runner="stub"` returns `stub`, `0/0` tokens and
  no error. `run --runner stub --json` then exits **0** with that same key present — without
  the guard it would have failed, and the review node would have REJECTED it.
- Tests **165 → 175**: `tests/test_thread_state.py` (4 — including the resume guard that
  keeps the reset scoped) and `tests/test_doctor.py` (4).

### Not fixed here

- TD-5.6-3 (the IDE model plane still has no table), TD-5.6-4 (`doctor` does not check MCP
  servers or the smoke task), TD-5.4-3 (mid-chain human gate), and the v4 harness items.
  All features or additions; none can produce a silently wrong result.

## v5.6.1 — Released (2026-09-19) — the ledger is a record, not a scratch file

**Theme:** a defect found while committing an engagement's install, and fixed rather than
documented away.

### Fixed

- **`ledger.render` REPLACED the whole file on every run.** It built three sections from the current state and did a wholesale `write_text`, so anything else living at that path was destroyed. Not hypothetical: it destroyed a **115-line hand-written task brief** in a real engagement, when an unrelated integration run wrote its own 18-line view over the top. Caught during a commit review and restored from `HEAD` before staging.
- `ledger.record` (was `render`) now **appends**: one section per run, keyed by thread, each wrapped in its own begin/end markers. Re-recording the same thread updates **its own** section — a run that steps three times leaves one section, not three — and nothing else is touched. Prose before, between or _after_ runtime sections survives exactly.
- Nothing is ever deleted: the file grows by one section per run.

### Changed

- `chain.py`, `cli.py` and `server.py` now pass the run's **thread** to the ledger, which is what makes "this run's own section" well-defined at all.
- `runcard.write` carries `decisions` too, so the structured card stands on its own instead of the decisions log being unique to the ledger.
- The install block's description of `.solar/ledger.md` is now **true**. It said "the human-view run record", which implied an accumulation the code did not perform — and a generated block that describes behaviour the runtime does not have is exactly the drift this whole line of work is about.

### Measured

- Live on a real repo: a hand-written brief placed at `.solar/ledger.md`, then three runs — two distinct threads plus a re-run of the first. Result: **the brief verbatim, and 2 sections rather than 3.** The re-run updated its own section instead of appending another.
- Tests **156 → 165**, with a new `tests/test_ledger.py` whose regression case is `test_hand_written_prose_at_the_ledger_path_is_never_touched`.

### Found while doing this, not fixed here

- **Reusing a thread id accumulates state.** `work_queue` and `decisions_log` are `operator.add` channels, so a second `run` on the same thread inherits the first run's lists — the live proof shows a doubled work queue and a doubled decisions log in one section. The default thread is a fixed `t1`, so this is the _normal_ path, not an edge case. TD-5.6-6.
- **`--runner stub` does not stub when a key is present.** `executor.run` falls back to the stub on a missing KEY, not on the selected runner, so the README's "Deterministic plan text (offline structure tests)" holds only while `SOLAR_API_KEY` is unset. TD-5.6-7.

## v5.6.0 — Released (2026-09-19) — install consistency

**Theme:** two installs of the same harness had drifted into **opposite** policies for the
same file, and neither recorded which version it was installed against. The cause was not
carelessness: `init` was destructive to re-run, so nobody re-ran it.

### Added

- **Model tiers** (TD-5.6-2). A model id could be written in five places, so a provider rename meant an edit per repo per file - and one non-existent id (`deepseek-v4-flash`) reached a config unreviewed. A repo can now declare `model_tier: "fast"` and the runtime resolves it from one table (`MODEL_TIERS`) keyed by the base-url family. Ladder: `SOLAR_MODEL` > role `model` > role `model_tier` > `cfg.model` > `cfg.model_tier` > default; an explicit id beats a tier **at the same level**, and a nearer level beats a further one. An unresolvable tier (unknown name, or unknown provider) sets `error` and fails the run, so the review node REJECTS instead of approving output from a model nobody asked for.
- **`.solar/VERSION`** — written by `init`, read by `doctor`, which WARNs when a repo's marker differs from the running runtime. Drift was previously invisible.
- **Marker-delimited `.gitignore` block** — rewritten by `init` on every run, so the ignore policy is one shipped decision rather than prose hand-argued per repo. Idempotent: a current block is left byte-identical.
- `doctor` gains an **`install`** check, and `_model_check` now catches an **IDE display name** in a runtime config (`"DeepSeek V4 Flash (deepseek)"`) and points at the API id it needs.

### Changed

- **`config.json` is portable.** `repo` was its only machine-specific field and it was a self-reference: the config already sits at `<root>/.solar/config.json`. It is now derived from the file's own location, omitted from the file when empty, and runtime-only fields are never persisted. A saved config contains nothing naming this machine, which is what makes committing it correct in every repo. An explicit `repo` still wins, for the unusual case of a config governing a different directory.
- **`init` merges instead of clobbering.** It overwrote `config.json` (losing a model pin) while writing `registry.json` only if absent - asymmetric, and the reason re-running it was avoided. Existing settings now win, new keys are added, and the output names what was `kept` and what was `added`. `--profile`/`--runner` now mean "override"; omitted, the stored value is kept.

### Fixed

- `init`'s `.gitignore` guard was `if ".solar/state" not in text`, which silently skipped the whole block if anything else had written that string - and could never revise a block it had written. Replaced by the marker block.
- Hand-written `.solar/...` rules that **conflict** with the block are now reported with real line numbers. Duplicates are deliberately not reported: Promyro carries four harmless ones and flagging them would bury the two rules in mandarin that actually mattered.
- The block writer emitted its own trailing newline, so rebuilding added a blank line and could never report `unchanged`. Caught by the idempotence test.

### Measured

- Live on a scratch repo: first `init` writes a config with **no `repo` key**; a hand-edited model pin then survives a refresh (`kept: model`), the block reports `unchanged`, and two conflicting hand-written rules are reported at `.gitignore:29` and `:30` without being deleted.
- Tests **141 → 155**, including a new `tests/test_install.py`.

### Not in this release

- **The IDE model plane has no tier table.** `.agent.md` frontmatter still hardcodes display names per repo; the new guard catches a transcription error, but there is nothing to rename centrally. TD-5.6-3.
- `doctor` still does not check MCP servers or the end-to-end smoke task, so §10's install list remains partly aspirational. TD-5.6-4.
- Engagement repos' `.solar/` data is still uncommitted, and both carry pre-existing unrelated modifications: sweeping those into a commit is the repo owner's call, not this runtime's.

## v5.5.0 — Released (2026-09-18) — the operator's surface: doctor, eval, uplink

**Theme:** the runtime could run; it could not tell you what it was about to do, whether
its quality signal applied to the repo in front of it, or where its records went. This
release closes the six remaining v5.4.x items.

### Added

- **`doctor` names the model that will actually run** (TD-5.4-6) — `<id> (from env SOLAR_MODEL | role | config | default)`, plus the roles whose own `model` overrides the config, plus `reasoning_effort` when set. With a key present it also asks the provider for its model list and reports **WARN** when the resolved id is neither served nor a known unlisted alias. Provenance comes from `executor.resolve_model`, now the single model ladder — a second copy would have drifted.
- **`eval` resolves cases per repo** (TD-5.4-4): `--cases <file>` > `<repo>/.solar/eval-cases.json` > the built-in battery. Running the built-ins against a repo they do not describe now prints a warning **before** the numbers, and the source travels in the aggregate as `cases_source`. A wrong signal is worse than no signal, because it gets acted on.
- **`uplink` is implemented** (TD-5.4-5): `uplink: none | hub:<url>`. `uplink.push` posts the curated run digest — routing, verdict, metrics, decisions, output _length_ — after the ledger and run-card are written. Push-only (there is no download path anywhere in the module), and it never raises: unreachable, refused or HTTP-erroring hubs degrade to a printed status line. `doctor` validates the value.
- **`reasoning_effort` pass-through** (TD-5.4-2) — `SOLAR_REASONING_EFFORT` > role `reasoning` > `cfg.reasoning_effort`, sent only when a level supplies one.

### Fixed

- **A `REJECTED` run exited `0`** (TD-5.4-10). `--json` documented "0 complete", and every `max_rounds` failure in the v5.4.1 integration test exited 0 while carrying `verdict: REJECTED` — so a wrapper driving on exit codes read a hard failure as a pass. `12` now means completed-but-rejected, on both the `--json` and one-shot paths.
- **Mandarin had no command vocabulary** (TD-5.4-7). `.solar/commands.json` now declares 20 vetted commands derived from its own `package.json`, and `frontend-engineer` (12), `backend-engineer` (12) and `docs-writer` (8) each carry an `exec_allow`. Destructive scripts are deliberately absent — `format`, `format:all`, `cleanup:radical-content`, `logs:prune` and `generate:system-map --emit` are not in the vocabulary, and `generate:system-map` is reachable only through its `--check` form.
- Mandarin's `.solar/config.json` pinned `deepseek-v4-flash`, which does not exist. The new `doctor` model check flagged it on first run; corrected to `deepseek-flash`.
- `doctor` now supports **WARN** as a third state (documented in §10, previously unreachable in the code): output marks it, and only `FAIL` produces a non-zero exit.

### Measured

- `doctor` on both real engagements: Promyro `model: PASS - deepseek-chat (from config) [provider serves 2 id(s)]` — no false alarm on an alias the provider serves without listing. Mandarin `model: WARN - deepseek-v4-flash ... not in the provider's model list (deepseek-flash, deepseek-v4-pro)` — the real bug, caught before a run rather than by one.
- Mandarin after the fix: 20 commands, **0 dangling grants** (every `exec_allow` name resolves in the vocabulary), `frontend-engineer` offered `run_command` + `write_file`, `code-reviewer` offered neither.
- Tests **127 → 141**.

### Not in this release

- **Mandarin's `main` battery is still not authored.** The mechanism is in place and the gap is now visible rather than silently wrong, but the cases themselves need ground truth from `main`, which is not this branch.
- `uplink` has no hub to talk to yet: the module is complete and tested against a refused connection, but no endpoint has consumed a digest.
- **TD-5.4-3** (mid-chain pause gate) is untouched.

## v5.4.2 — Released (2026-09-18) — the runner can be chosen per run

**Theme:** the v5.4.1 integration test had to edit a live engagement's
`.solar/config.json` — twice — because there was no way to choose a runner for one run.
There is now.

### Added

- **`run --runner {agent-dispatch,http,stub}`** — picks the runner for that run only. It sets `SOLAR_RUNNER` for the process rather than writing `config.json`, so the committed config is never touched and the flag and the env knob cannot disagree about which runner won.
- `executor.RUNNERS` — the three runner ids, so the CLI offers them as `choices=` instead of repeating the list.

### Fixed

- **`SOLAR_RUNNER` was unreachable.** `select_runner` was `cfg_runner or os.environ.get("SOLAR_RUNNER", "")`, so a repo whose `config.json` pinned a runner **always** won and the documented env override did nothing — the opposite of `SOLAR_MODEL`, where env beats both role and config. The ladder is now `SOLAR_RUNNER` > config > auto.
- **A typo no longer downgrades silently.** `select_runner` raises on an unrecognised runner instead of falling through to auto: `runner: "https"` used to select a _different_ runner than the config asked for, with no signal. `doctor` reports it as `FAIL runner`, and `/health` returns `runner: "invalid"` plus `runner_error` rather than failing the endpoint.

### Measured

- Acceptance test on the exact case that forced the config edits: `--runner http` against Promyro, whose config pins `agent-dispatch` — 8 tool calls, 26,848 tokens, `forced_final: false`, verdict APPROVED, and `config.json` reporting `"runner": "agent-dispatch"` **before and after**.
- Tests **123 → 127**.

### Corrects

- `README.md` described the runner as "`cfg.runner`, or env `SOLAR_RUNNER`" with no precedence. It now states the ladder and documents the per-run flag.

## v5.4.1 — Released (2026-09-18) — the specialist tool loop terminates

**Theme:** v5.4.0 gave the `http` runner capacity; this release makes it _finish_. The
verification of v5.4.0 on a real repo found the loop returning **no answer at all** in 4
runs out of 5 — on a read-only role, over a one-file one-fact objective.

### Added

- **A termination rule for the tool loop** (`executor._tool_loop`) — three parts, each traced to a measurement: an explicit **`temperature`** (default `0.2`; `SOLAR_TEMPERATURE=default` omits the field for gateways that reject it); a **budget notice** once `NUDGE_ROUNDS_LEFT` (1) tool rounds remain; and a **final round called with no tools offered at all**, so the response has to be text. A node that cannot finish now hands back what it established, naming its gaps, instead of failing the run.
- **`forced_final`** on the executor result → graph state → `--json` step summary → run-card, so _answered_ is distinguishable from _cut off, and answered anyway_.
- 12 tests driving the loop against a scripted fake client that records the exact payload per round — including that the final round carries no `tools` key.

### Changed

- `executor.run` now builds the client and messages and delegates to `_tool_loop`. The loop is driven without a network call, which is what made the termination rules testable at all.
- `core.SolarState` gains `forced_final`; `graph._execute` carries it; `runcard.write` and `cli._state_summary` surface it.

### Fixed

- **The loop had no stop rule.** `error: "max_rounds"` — "reached max tool rounds without a final answer" — was reachable on ordinary read-only work and cost ~170k prompt tokens per failed run. Exhausting the round budget no longer fails the run; the remaining failure mode is `error: "empty_output"` (a final round that returns no text), reported distinctly.

### Measured

- `investigator`, read-only `http` link, one clone, one file, one fact: **failing run 21 calls / 168k tokens / no answer**; the **identical command** next run **5 calls / 19k tokens / answered and APPROVED**. Same repo, role, prompt, objective, model, cap.
- Not the model — `deepseek-chat` and `deepseek-flash` both failed. Not the cap — 12 → 24 doubled tool calls 23 → 46 and still did not answer.
- Tests **111 → 123**.

### Corrects

- `docs/tuning.md` finding 3 concluded the decisive lever on heavy tasks is the _objective_ ("be efficient, batch reads, stop once verified"), not the cap. The failing objective here was one file with the words "Nothing else" — **the lever was never the objective.** §20 of `docs/versions/v5.md` carries the measurements.

### Not in this release

- `SOLAR_RUNNER` still cannot override a repo's `config.json` (`select_runner` prefers the config), so forcing `http` on a repo configured for `agent-dispatch` still needs a config edit — TD-5.4-9.
- A run whose verdict is `REJECTED` still exits `0` under `--json`, where the contract says `0` means complete — TD-5.4-10.

## v5.4.0 — Released (2026-09-18) — HTTP runner capacity without a shell

**Theme:** give `--runner http` full role capacity **without giving it a shell**. On this
runner there is no supervisor — the light profile's tiny tool set _was_ the substitute for
supervision — so what is added here is containment, not capability for its own sake. Every
rule below traces to a measurement.

### Added

- **`read_file(rel, start, end)` line ranges** (Part A) — 1-based inclusive, clamped to the file, erroring past the end, and **bypassing the 40000-char whole-file cap** so a large file is read in bounded slices instead of truncated mid-file. The range params are advertised in `tool_schemas()`: a param absent from the schema is a param the model never sends.
- **Write policy** (Part B) — an **unconditional** deny-list (`.solar/`, `.git/`, `.github/`, `.vscode/`, plus `package.json`/`pyproject.toml`/`requirements.txt`/`Dockerfile`/`.mcp.json`, matched case-insensitively on any path segment at any depth), plus per-role `write`/`write_scope`/`write_deny`. **Closes a live hole: `.solar/registry.json` is the agent's own system prompt and was writable with no shell needed.**
- **Role-gated tool schemas** (Part B1) — `tools` finally does something: a read-only role is never _offered_ `write_file`, and `write_file` refuses anyway (a model can emit a call for a tool it never got). A role without `exec` is never offered `run_command`.
- **Vetted command vocabulary** (Part C) — `.solar/commands.json`: fixed argv, **no free-text command or argument field**, per-role `exec_allow`. `cwd` is repo-relative and confined; `timeout` enforced; output ANSI-stripped and clipped keeping head **and** tail. `exec` defaults to NOTHING (opt-in), deliberately unlike `write`, which had to default to allowed for compatibility.
- **Tool-enforced approval gate** (Part D) — `kind: act` with `human_approval` means the command **does not run**: it writes `.solar/approvals/<id>.md` and returns `AWAITING APPROVAL <id>`, so the model cannot proceed. Everything a human reads is config-derived; the id derives from the command, not the round.
- **Shaped checker output** (Part E) — `kind: check` + exit 0 collapses to one line; a failure keeps its failures, always the final summary line, and states how many lines it suppressed. `shape.summary_only` / `shape.keep` / `shape.max_items` override. `kind: read` is never summarised.
- **Per-node model routing** (absorbs TD-5.4-1) — `SOLAR_MODEL` → role `model` → `cfg.model` → default, skipping empty levels. `write_handoff` names the resolved model.

### Changed

- `graph._role_spec` returned `(role, system)` and **dropped every other registry key**, so no role policy could reach the tool layer; it now returns the full dict (`_role_prompt` helper added, both call sites updated).
- `executor.run` takes `spec` and `human_approval`; the tool layers compose behind one dispatch surface.
- `server.py` no longer hand-duplicates `__version__` — it imports it, so `/health` cannot drift from the package (it held a second literal at L45).
- `docs/versions/v5.md` §6 (registry keys + why capability rather than prose), §8 (light-profile write-guard and model rows), §10 (guard scope, approval gate, shaped checks), status header.

### Fixed

- Windows `.CMD` resolution: `shell=False` cannot execute an `npm` shim (`WinError 2`), so `argv[0]` is resolved through `shutil.which` (git worked, npm did not — both were tried).
- Windows exit codes normalised from the 32-bit DWORD (`4294963238` → the signed value).
- ANSI escapes stripped from tool output.

### Measured

- Shaped vs unshaped on the same real checkers (client monorepo): `format_check` 4282 → **368** chars (−91%, 581 lines suppressed) · `lint` 1351 → **107** (−92%) · `typecheck` 135 → 115.
- `npm --silent` verified as source-level noise removal: success → 0 chars; failure → exit code **and all 30983 chars of stderr preserved**, so a failing checker cannot go quiet.
- Tests **28 → 111**. New `tests/test_workspace.py` and `tests/test_commands.py`.

### Not in this release

- **No sandbox.** The container front is still separate work; this narrows what needs sandboxing to a closed command set.
- **No shell, permanently, for the light profile.**
- **The approval gate ships inert** — every command in the reference vocabulary is `read` or `check`, so nothing is gated in production yet. It is exercised by a synthetic `act` command in tests.
- `docs/install-mandarin-main.md` stays pinned to v5.3.1 by choice: it records one install event and is updated on re-install.

## v5.3.1 — Released (2026-09-05) — driver-orchestrated only (self-chain removed)

**Theme:** remove the last falsified-model surface from the runtime — chains are
driver-orchestrated, full stop.

### Removed

- **Bare `--chain` self-running entry dispatch** — `run --chain <name>` without
  `--auto` used to dispatch the chain ENTRY and tell it to run the whole chain
  itself; the mandarin pilot FALSIFIED agent-spawns-agent chaining. `--chain`
  now REQUIRES `--auto` (headless driver, one run-card per link); in the IDE the
  Governor agent drives each link as its own `--role` dispatch.
- **`POST /run` with `chain`** — the one-step chain-entry path is gone; headless
  chains run via `POST /chain` (auto). `POST /run` accepts a single `role`.
- **"CHAIN ENTRY / run the rest yourself" handoff text** — a dispatched
  specialist handoff now carries only neutral chain context ("you are ONE link;
  the coordinator runs the other links; never spawn or compose the chain
  yourself").

### Changed

- `executor.write_handoff` chain note → driver-framed (no self-run instruction).
- `graph._chain_note` / `_dispatch_agent` note text + docs updated.
- Version bump `5.3.0` → `5.3.1` (pyproject + `__version__`).
- CLI `--chain` / `--auto` help text updated to the driver model.

---

## v5.3.0 — Released (2026-09-05) — Governor-as-graph (LangGraph)

> **Version note:** this is the **v5.3** track (governor-as-graph). **v5.2** = agent-consistency enforcement (see `docs/research/v5-agent-consistency-*.md` + `docs/work-logs/v5.2-consistency-implementation-plan.md`). All folded into the v5 line; each sub-version is a clean commit bucket.

**Theme:** Governor-as-graph (LangGraph) — v5 plan + B2 prototype + solar-governor runtime.

### Added

- **solar-governor runtime (dev)** (`solar-governor/`) — v5 implementation step 1 (2026-09-04): light-profile graph + SQLite checkpoint + CLI (`init`/`run`/`doctor`) + ledger render + deterministic routing + stub executor; 5 smoke tests pass. Next: mandarin registry + model executor + workspace tool.
- **`run --json` step contract** (2026-09-05) — `run` executes ONE graph step and exits 0 (complete) / 10 (agent-dispatch) / 11 (review) / 2 (guard error) with a machine-readable JSON doc, so a thin driver agent (not a human at stdin) can loop: dispatch specialist on 10, ask the human on 11. Adds `run_step`/`pending_interrupt` (cross-process resume via SQLite), a `role`+`attempt` field on the agent-dispatch interrupt payload, refactors `run_task` onto `run_step` (13 tests pass). Paused-thread guard prevents wrong-value resumes.
- **Governor v5 driver agent** (mandarin `.github/agents/governor-v5.agent.md`) — the v4-like single UI entry point for the graph: reads the interrupt JSON, maps `role`→repo agent, dispatches the specialist, saves its answer to `<handoff>.result.md`, resumes; surfaces review gates. Engine stays vendor-agnostic; only this thin shell is IDE-specific.
- **Named-chain dispatch (self-chain)** (2026-09-05) — the "agents chain themselves" model: registry gains data-driven `chains` (name → ordered roles; a nested list = a parallel group). `run --chain <name>` dispatches ONLY the chain ENTRY; the handoff marks it CHAIN ENTRY and embeds the chain, so the entry agent runs the whole chain via direct agent-to-agent delegation (no return to Governor/Orchestrator between links) and returns the FINAL result. Adds `registry.chain*`/`role_keys`, a `chain` field on state + run-card, chain-aware dispatch, and a doctor role-count fix (structural keys excluded). Mandarin `epic` chain = `investigator → architect → uiux-designer → (frontend-engineer + backend-engineer) → docs-writer → code-reviewer`. 17 tests pass. (Trade-off chosen deliberately: per-hop run-cards/gates are traded for one run-card per epic; the governor is entry + final gate only, and human-owned gates like the UIUX Preview Gate still pause the chain.)
- **⚠️ Pilot correction — driver-orchestrated chaining (2026-09-05):** the agent-spawns-agent self-chain above was **FALSIFIED** on Copilot — nested agents lack the agent-spawn tool. Final v5.3 model: `--chain <name> --auto` runs every link headless in order (one run-card per link); in the IDE the Governor driver runs each link. See `docs/versions/v5.md` + mandarin `PILOT.md` caveats.
- **`--role` pin + Hermes intake** (2026-09-05) — `run --role <role>` pins dispatch to one registry role (skips keyword classify), so the Hermes intent-decoder can hand the manager a concrete role and get a deterministic run; mutually exclusive with `--chain`, validates the role exists. Registry role detection keys on a role's `system` prompt so `playbooks` entries (which carry a `role` slot) are never miscounted or misrouted. 19 tests pass.
- **Headless HTTP API + bench** (2026-09-05) — `solar-governor serve` runs a zero-dependency stdlib HTTP server (`GET /health`, `POST /run` — one graph step, same shape as `run --json`, resumable via `result`/`approve`) so any client/platform can run tasks without an IDE or an interactive shell (v5 §9 'remote later' slice). `solar-governor bench --task … --n N` runs the same task N times over the `http` runner and aggregates real tokens/duration/tool_calls. Env-key presence now makes `test_executor` non-deterministic, so unit tests force a key-less env. 22 tests pass.
- **Tool-output truncation + known-answer eval battery** (2026-09-05) — the epic-25 verify chain exposed runaway context (read-heavy roles reached 300–555k prompt tokens). `SOLAR_TOOL_OUTPUT_CHARS` (default 8000 after tuning; was 12000; 0 = unlimited) now caps each tool result kept in context. New `solar-governor eval` runs a deterministic known-answer battery (default read-only cases on mandarin: shared entries, chengyu phase, route count, guest badge testid, TTS guard, cn join) and reports pass-rate + tokens + est $ — a real quality signal for tuning (unlike auto-APPROVED verdicts). 28 tests pass.
- **v5 plan doc** (`docs/versions/v5.md`) — governor-as-graph design: 3-layer architecture (LangGraph control / MCP tool / repo data-context), state schema grounded on the real 3-section ledger, node map, specialist registry + compactor, light/full profiles, one-engine 4-front install, verifiability (doctor + operational eval), data sovereignty (repo-bounded, uplink opt-in), v4→v5 migration.
- **B2 governor-graph prototype** (`experiments/governor-graph/`) — 6 evals, all PASS: deterministic routing, HITL interrupt, SQLite durable checkpoint (cross-process resume), streaming, compactor (37% token ratio), hub KB MCP call + graceful degradation.

### Changed

- **Decision (B2 gate):** ADOPT v5 on graph → proceed to full migration (see `docs/versions/v5.md` §17). First deployment = the master repo (resume-kb) as dogfooding.
- `TODOs.md`: added TD-5-1 (v5 plan), supersedes TD-4-1/2/3/4/5.
- **v5.3.0 release (2026-09-05)** — tagged from the `v5` branch after the
  mandarin pilot. Evidence: T1–T5 PASS + epic-25 Phase A delivered
  (driver-orchestrated, not autonomous) + verify close-out Code Reviewer
  APPROVED; eval battery 18/18 across tuning settings (truncation 8000 vs
  off, rounds 6 vs 12); whole pilot day ≈ $0.11 (input ~77% cache-hit).
  `solar-v5-wire` is kept as **reference-only** pilot proof; the full epic-25
  with the detailed pipeline runs on `main` after installing v5.3.0.

## v5.1.0 — July 10, 2026

**Theme:** Context-efficiency overhaul — dedicated Context Summarizer agent, read-tool restriction on specialists, shrunk artifact schemas.

### Added

- **Context Summarizer agent** (`context-summarizer.agent.md`) — new agent with exclusive `read` tool access. Reads source files before every specialist dispatch and produces a compact digest (`{task-id}-digest.json`). Only agent allowed to `read` source files.
- **Context Summarization skill** (`context-summarization/SKILL.md`) — instructions for producing compact digests with `refs[]`, `facts[]`, and `warnings[]`.
- **Context budget rule** in solar.prompt.md — after every 3 specialist dispatches, governor performs a context roll-up: summarizes completed stages into a single Decisions Log entry and clears stale file contents from working memory.

### Changed

- **All 6 specialist agents** — `read` tool removed from tool lists. Context arrives via compact digest passed inline by Governor, not via direct file reads.
- **All artifact schemas** — stripped to minimal refs-only format: `{task_id, refs[]}` + stage-specific fields. Substantive content (findings, reasons, summaries) goes to Decisions Log, not artifacts.
- **All skill SKILL.md files** — steps updated: specialists extract context from dispatch prompt (Governor includes digest inline) instead of reading files directly. Compact-handoff schema references removed.
- **All 3 playbook SKILL.md files** — Context Summarizer dispatch added before each specialist stage. Renumbered all steps.
- **Agent Registry & Skill Index** (AGENTS.md) — Context Summarizer row and context-summarization skill registered.
- **solar.prompt.md** — new step 3b (CONTEXT) added before 3c (EXECUTE): dispatch Context Summarizer, read digest, pass inline. Stale Materials section (step 5) replaced with Context Summarizer discipline and Artifact discipline rules. Context roll-up rule added to step 7.
- **Reference docs** (concept, reference, implementation guideline) — updated with Context Summarizer description, read-tool restriction pattern, and updated agent/skill counts.

### Design Rationale

- **Cheap writes, expensive reads**: writing a compact digest (~200 tokens) costs pennies via DeepSeek V4 Flash. Reading source files into context costs 500-5000+ tokens. By centralizing reads in one agent and passing compact digests inline, we prevent context bloat from incidental file exploration.
- **Tool restriction as architecture**: blocking `read` from specialists means they cannot accidentally expand scope by exploring files. They get exactly what the summarizer determined they need.
- **Artifact-as-reference**: artifacts now serve as routing metadata only — the substantive content lives in the Decisions Log (governor-accessible) or in the source files themselves (not loaded into context unless needed).

## v5.0.0 — July 10, 2026

**Theme:** Lightweight simplification — stripped v4.6.3's token-efficiency machinery in favor of a simpler, cheaper-model-optimized harness.

### Removed

- **PreToolUse hook** (`pre-tool-use.cjs`) — baton field enforcement, signal routing, DISPATCH_TOO_LARGE gate, and DUPLICATE_READ_DETECTED tracking removed. These optimized for expensive tokens ($/token); with DeepSeek V4 Flash at ~$0.15/M input, the savings no longer justify the complexity.
- **Stop hook** (`stop.cjs`) — Completion Promise enforcement removed. The Ralph loop state machine is simplified; a simple max-iteration guard in the governor suffices.
- **Read tracker + telemetry** (`common.cjs` functions `loadReadTracker`, `saveReadTracker`, `appendTelemetry`, `collectPreToolUseSignals`) — stripped. All tracker/telemetry infrastructure removed.
- **Dispatch Payload Contract** — the 4-field baton enrichment (`ledger_stage`, `artifact_refs`, `agents_md_section`, `input_refs[]`) removed from docs, governor, and enforcement. Pre-loading saved 1-2 turns at pennies each — not worth the gate infrastructure.
- **Config expansion fields** — `solar.config.json` reduced from 14 to 5 flags: `adversarial`, `learning`, `logging`, `human_approval`, `hooks`. Removed: `maxDispatchInputTokens`, `maxHighCostDispatchTokens`, `maxReadWindowLines`, `maxReadsPerFilePerSession`, `requireArtifactRefForHighCost`, `enforceDeltaForRedispatch`, `artifactizationThresholdTokens`, `hardFailSignals`, `ledgerCompactionThreshold`, `telemetry`.
- **Model tiering** — all agents now default to single-model assignment (DeepSeek V4 Flash). Removed the 3-tier model policy (GPT-5 mini / GPT-4o / Claude Sonnet 4.5). Premium model is optional for architect/security roles.

### Changed

- **`common.cjs`** — reduced from 5 exported functions to 3 (`loadConfig`, `readLedger`, `isSolarActive`). All tracker, telemetry, and signal collection code removed.
- **`hooks.json`** — reduced from 3 hooks to 1: only `PostToolUse` remains. `PreToolUse` and `Stop` entries removed.
- **`orchestration-governor.agent.md`** — removed Dispatch Baton Rule, Task Tracker Initialisation, and Proactive Compaction sections. Model changed from `Claude Sonnet 4.6 (copilot)` to `DeepSeek V4 Flash (deepseek)`.
- **`.ai_ledger.md` template** — simplified from 5 sections to 3: `Objective`, `Work Queue`, `Decisions Log`. Removed Loop State, Materials table, Completion Promise.
- **`AGENTS.md`** — ledger template simplified, hook config reduced, model version bumped to `5.0.0`.
- **`docs/solar-ralph-reference.md`** — removed Dispatch Payload Contract, Pre-Tool-Use Signals, Artifact-Scoped Tracker, and tiered Model Policy sections. Layer 3 hooks simplified. Layer 11 ledger template simplified.
- **`docs/solar-ralph-concept.md`** — removed Materials section from sparse document, simplified dispatch baton description, removed iteration column from Work Queue.

### Added

- **Direct context dispatch** replaces baton enforcement: "include the current stage, relevant artifact paths, and the specialist's registry entry" — guidance, not gates.

---

## v4.6.3 — May 24, 2026

**Theme:** Token-efficiency hardening — baton enrichment, compact-handoff schema, pre-tool-use gate, config expansion.

### Added

- **Dispatch Payload Contract** (`docs/solar-ralph-reference.md`) — new `## Dispatch Payload Contract` section defines the four universal baton fields (`ledger_stage`, `artifact_refs`, `agents_md_section`, `input_refs[]`) required in every `runSubagent` call. Previously undocumented; absence caused project-specific fields to leak into generic dispatch patterns.
- **`compact-handoff-packet.schema.json`** — new schema added to both `template/.github/solar-system/schemas/` and as verbatim installer output (step 5H). All specialist artifact write-output steps now reference this schema for required envelope fields (`schema_version`, `task_id`, `stage`, `changed_items`, `decisions_delta`, `blockers_delta`, `acceptance_criteria_delta`, `artifact_refs`, `author`, `written_at`).
- **`collectPreToolUseSignals()`** (`template/.github/hooks/common.cjs`) — new hook function enforcing baton field presence on every `runSubagent` dispatch. Emits `DELTA_HANDOFF_SCHEMA_MISSING` when `ledger_stage` or `artifact_refs` are absent from the dispatch prompt. Added as 4th export alongside `loadConfig`, `readLedger`, `isSolarActive`.
- **`solar_version: "4.6.3"`** field added to `template/.github/AGENTS.md` §1 and installer AGENTS.md §1 output.

### Changed

- **`solar.config.json`** (template + installer) — expanded from 5 to 14 fields: added `maxDispatchInputTokens`, `maxHighCostDispatchTokens`, `maxReadWindowLines`, `maxReadsPerFilePerSession`, `requireArtifactRefForHighCost`, `enforceDeltaForRedispatch`, `artifactizationThresholdTokens`, `hardFailSignals`, `telemetry`.
- **`orchestration-governor.agent.md`** (template + installer) — added `## Dispatch Baton Rule` section: four required baton fields, enforcement rule, material gate linkage. Governor now fails G1 gate if any baton field cannot be populated.
- **All 10 `SKILL.md` files** (template + installer) — write-output steps updated to reference compact-handoff schema required fields. Playbook skills (implement-feature, bug-fix, create-doc) include trailing `**Compact-handoff contract**` note; recursive-remediation includes all-artifact coverage note.
- **`docs/solar-ralph-concept.md`** — added Dispatch baton bullet under Orchestrator section: Governor Baton Enrichment pattern now documented as a first-class orchestration behaviour.

### Fixed

- **Baton field universality** (`docs/work-logs/solar-token-optimization-proposal.md` §5C) — removed `story_br_path` and `story_impl_path` (mandarin-specific fields that leaked into the universal spec). Replaced with `input_refs[]` — a generic array populated project-specifically.
- **`collectPreToolUseSignals` was dead-wired** — the function existed in `common.cjs` but was never invoked because no `pre-tool-use.cjs` script existed and `PreToolUse` was not registered in `hooks.json`. `DELTA_HANDOFF_SCHEMA_MISSING` could never fire. Fixed by: creating `pre-tool-use.cjs` in both `template/` and installed repos; registering `PreToolUse` in `hooks.json`; updating installer to generate the script as a core hook (removed from Optional list); updating §6 hook table.

---

## v4.6.3 addendum — May 30, 2026

**Theme:** Dispatch telemetry, artifact-scoped tracker, oversized-dispatch gate, and installer split.

### Added

- **`DISPATCH_TOO_LARGE` hard-fail signal** (`template/.github/hooks/pre-tool-use.cjs` + `common.cjs`) — fires when `JSON.stringify(tool_input).length > maxDispatchInputTokens × 4`; hard-fail exit 2 message: "Move artifact bodies to `verification-artifacts/` and pass paths only, then retry." Added to `hardFailSignals` array in `solar.config.json`.
- **`appendTelemetry()`** (`template/.github/hooks/common.cjs`) — new helper; appends one JSONL entry per `runSubagent` dispatch to `verification-artifacts/{task_id}-telemetry.jsonl`. Entry shape: `{ ts, sessionId, task_id, tool, input_chars, est_tokens }`. Guarded by tracker-file existence — no-op when no active SOLAR task.
- **`## Task Tracker Initialisation`** section (`template/.github/agents/orchestration-governor.agent.md`) — Governor must write `{ "task_id": "<id>", "reads": {} }` to `verification-artifacts/<task-id>-tracker.json` before the first dispatch of any new task. Until the file exists all hook read-tracking and telemetry are silently inactive.
- **`solar-install-inventory.md`** — new 1306-line verbatim inventory file; 31 `## INV:<slug>` sections each containing `<!-- Target: <path> -->` and a verbatim fenced code block. Separates all file bodies from orchestration logic.

### Changed

- **Artifact-scoped tracker** (`template/.github/hooks/common.cjs`) — tracker path moved from `.github/.read-tracker.json` (caused VS Code JSON-schema validation errors) to `verification-artifacts/{task_id}-tracker.json`. `loadReadTracker()` returns `null` when file absent — hook skips all tracker logic silently. `saveReadTracker()` is a no-op when file absent. Orchestrator creates the file to arm enforcement; hook never auto-creates it.
- **`solar-install.prompt.md`** — split from 1615-line monolith to 449-line lean orchestration prompt. All verbatim file bodies moved to `solar-install-inventory.md`; installer references them via `→ Read INV:<slug> from solar-install-inventory.md and write verbatim to <path>.` directives.

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
