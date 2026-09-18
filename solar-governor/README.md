# solar-governor — SOLAR-Ralph v5 runtime

The LangGraph control layer for SOLAR v5 (governor-as-graph). Small, installable,
repo-bounded. See `../docs/versions/v5.md` for the full design.

## Status

Released (**v5.6.1** — install consistency, and a ledger that is a record). The runner
work: full role capacity without a shell (line ranges, write policy, a closed command
vocabulary, an approval gate, shaped checkers, per-node model routing); a tool loop that
terminates (`v5.4.1`); a runner choosable per run (`v5.4.2`). `v5.5.0` added the
operator's surface: `doctor` names the model that will actually run, `eval` resolves cases
per repo, `uplink` posts the run digest. `v5.6.0` made an install portable and re-runnable:
`config.json` stores no absolute path, `init` merges instead of clobbering,
`.solar/VERSION` records what the repo was installed against, the `.gitignore` block is
generated, and repos declare a model **tier**. **v5.6.1** makes `.solar/ledger.md` an
append-only record — one section per run, and hand-written content in it is never touched.
Pilot-validated on the mandarin repo (branch
`solar-v5-wire`, kept as reference proof): T1–T5 PASS, epic-25 Phase A
delivered, driver-orchestrated verify close-out APPROVED, known-answer eval
battery 18/18. Chaining is **driver-orchestrated** — agents never self-chain
(nested agents lack a spawn tool): headless `--chain <name> --auto`, or the
Governor agent drives each link as its own `--role` in the IDE. Next: install
into the target repo's `main` and run the real epic with the full pipeline.

## Compatibility with v4 / v5.x

`solar-governor init` writes **`.solar/`** (NEW — runtime state: config.json,
registry.json, `state/` checkpoints, ledger.md) and leaves the **`.github/`**
harness untouched (v4/v5.x agents + hooks coexist; the graph dispatches to them
via the shape-a write adapter). Two different dirs on purpose: `.github/` = the
agent harness, `.solar/` = the v5 graph runtime. v4 users will see a new folder
but nothing moved or broken.

## Commands

```bash
solar-governor init   --repo <path> --profile light          # create OR refresh .solar (never clobbers your settings)
solar-governor doctor --repo <path> [--json]                 # install self-check (PASS/FAIL)
solar-governor run "<task>" --repo <path>                    # one task through the graph (ledger + run-card)
solar-governor run "<task>" --repo <path> --role <role>      # pin one specialist (e.g. Hermes decision)
solar-governor run "<task>" --repo <path> --runner http      # choose the runner for THIS run only
solar-governor run "<task>" --repo <path> --chain <name> --auto   # whole chain, driver-orchestrated, headless
solar-governor serve --repo <path>                           # headless HTTP API (POST /run, POST /chain)
solar-governor bench "<task>" --repo <path> --n 5            # N-run aggregate (tokens/time/verdict)
solar-governor eval   --repo <path> --n 3                    # known-answer battery (quality signal)
```

Run without installing: `python -m solar_governor.cli ...` from this directory.

### Re-installing (safe, and meant to be re-run)

`init` **merges**: a setting the repo chose is kept, a key a new version introduces is
added, and the output says which was which. It also rewrites the marker-delimited
`.gitignore` block in place and writes `.solar/VERSION`.

```bash
solar-governor init --repo <path>       # refresh: keeps model/runner/human_approval
solar-governor doctor --repo <path>     # 'install' WARNs when the marker has drifted
```

A hand-written `.solar/...` rule that **conflicts** with the generated block is reported
with its line number and left alone — a duplicate of a block rule is not reported, so the
warning means something. `config.json` stores no absolute path, so it is safe to commit,
and a stale model pin can therefore show up in a diff.

### Model tiers (so a provider rename is one edit)

Instead of a concrete id, a repo or a role may declare a **tier**:

```json
{ "model_tier": "fast" }
```

`MODEL_TIERS` in the runtime maps a tier to the provider's current id. Ladder:
`SOLAR_MODEL` > role `model` > role `model_tier` > `cfg.model` > `cfg.model_tier` >
default — an explicit id beats a tier **at the same level**. An unknown tier, or a tier
asked of an unknown provider, fails the run rather than silently picking a model.
Chains are **driver-orchestrated**: a bare `--chain` (no `--auto`) is rejected
— run headless with `--auto`, or in the IDE drive each link as its own
`--role` from the Governor agent.

## Tool layers — what a role is actually offered (v5.4.0)

A specialist gets two tool layers, each **gated by the role's registry entry**. A tool the
role may not use is **not offered at all** — it is not a rule in the prompt:

| Layer       | Tools                                          | Gated by                                              |
| :---------- | :--------------------------------------------- | :---------------------------------------------------- |
| `workspace` | `list_tree`, `read_file`, `glob`, `write_file` | `tools` (group), `write`, `write_scope`, `write_deny` |
| `exec`      | `run_command`                                  | `tools` (group), `exec_allow`                         |

`read_file(rel, start, end)` takes a 1-based inclusive line range, and a ranged read
**bypasses the 40000-char whole-file cap** — so a large file is read in bounded slices
instead of being truncated mid-file and re-read.

### The write guard

Root confinement is always enforced. On top of it an **unconditional** deny-list refuses
writes to `.solar/`, `.git/`, `.github/`, `.vscode/` and to agent/CI-defining files
(`package.json`, `pyproject.toml`, `requirements.txt`, `Dockerfile`, `.mcp.json`, …),
matched case-insensitively on any path segment at any depth. This closes a live hole:
`.solar/registry.json` **is the agent's system prompt**, and it used to be writable.

## `exec` — a closed vocabulary, not a shell

A repo declares named commands with **fixed** argv in `.solar/commands.json`, and a role
may only run the names it is granted:

```jsonc
{
  "typecheck": {
    "argv": ["npm", "--silent", "run", "typecheck"],
    "cwd": "apps/web",
    "kind": "check",
    "timeout": 180,
  },
  "git_status": {
    "argv": ["git", "status", "--short"],
    "kind": "read",
    "timeout": 30,
  },
}
```

| Field      | Meaning                                                                                                                       |
| :--------- | :---------------------------------------------------------------------------------------------------------------------------- |
| `argv`     | fixed, never model-supplied. There is no free-text command field **or** argument field.                                       |
| `cwd`      | repo-relative (default: the repo root), confined to the repo.                                                                 |
| `kind`     | `read` (the output IS the information) · `check` (shaped; a pass is one line) · `act` (needs approval when `human_approval`). |
| `timeout`  | seconds, enforced.                                                                                                            |
| `shape`    | `{ "summary_only": true }` or `{ "keep": "<regex>", "max_items": N }`, for checkers whose raw output is mostly noise.         |
| `describe` | the only prose a human is shown at an approval gate — from config, never from the model.                                      |

An entry's `argv[0]` is resolved through `shutil.which`, because `shell=False` cannot
execute a Windows `.CMD` shim (`npm` would raise `WinError 2`; `git` is a real `.EXE`).

**Absence is the mechanism.** A command the repo does not declare does not exist; a command
it declares but does not grant to a role does not exist _for that role_ — and the error says
which case applies, so a fixable config problem is distinguishable from a missing command.

### Approval gate

With `human_approval: true` a `kind: act` command does **not** run. It writes
`.solar/approvals/<id>.md` and returns `AWAITING APPROVAL <id>` — the tool cannot proceed, so
the model cannot either. A human writes `allow` or `deny: <reason>` to
`.solar/approvals/<id>.decision`. The id derives from the command, not the round, so a
decision is never re-asked.

## Runners — how a specialist executes (provider-agnostic)

The graph never calls a provider directly. The SPECIALIST node asks a **runner**. The
ladder is `run --runner X` (this run only) > `SOLAR_RUNNER` > the repo's `cfg.runner` >
auto (http if a key is set, else stub). An unrecognised value is an **error**, not a
silent fallback — a typo must not select a different runner than the one asked for:

| Runner           | What it does                                                               | Needs                 |
| ---------------- | -------------------------------------------------------------------------- | --------------------- |
| `agent-dispatch` | Writes a task handoff (`.solar/handoffs/`), interrupts; you run the repo's | VS Code Copilot + the |
|                  | `.agent.md` specialist in the IDE (DeepSeek via the DeepSeek-for-Copilot   | DeepSeek extension    |
|                  | extension), then paste the result (or result-file path) to resume          |                       |
| `http`           | OpenAI-compatible chat call with repo-bounded workspace tools              | `SOLAR_API_KEY`       |
| `stub`           | Deterministic plan text (offline structure tests)                          | nothing               |

Set the runner per repo at install time:

```bash
solar-governor init --repo <path> --runner agent-dispatch   # IDE-native pilot
solar-governor init --repo <path> --runner http             # headless/CLI
```

Or override it for a **single run**, without touching the committed config — so a repo
pinned to `agent-dispatch` can be exercised through `http` (or the reverse) and handed
back unchanged:

```bash
solar-governor run "<task>" --repo <path> --runner http
solar-governor run "<task>" --repo <path> --role investigator --runner stub
```

### `http` runner config (env only, never committed)

```bash
$env:SOLAR_API_KEY  = "<your deepseek/openrouter key>"   # or DEEPSEEK_API_KEY
$env:SOLAR_BASE_URL = "https://api.deepseek.com"          # default; any OpenAI-compatible host
$env:SOLAR_MODEL    = "deepseek-chat"                     # or cfg.model
$env:SOLAR_RUNNER            = "http"    # same as `run --runner http`
$env:SOLAR_TEMPERATURE       = "0.2"     # tool-loop sampling; "default" omits the field
$env:SOLAR_REASONING_EFFORT  = ""        # provider pass-through; unset sends nothing
$env:SOLAR_MAX_ROUNDS        = "12"      # model round-trips per node (read at import)
$env:SOLAR_TOOL_OUTPUT_CHARS = "8000"    # cap on one tool result, 0 = unlimited (read at import)
```

Tools (repo-bounded, refuse to escape the repo root): `list_tree` / `read_file` /
`glob` / `write_file`, plus `run_command` for a role with an `exec_allow` grant.

### Hub uplink (opt-in, push-only)

`uplink: none | hub:<url>` in `.solar/config.json`. The default is `none`: the repo is
the source of truth and the harness is fully standalone on any repo, including
third-party ones. When set, the run digest — routing, verdict, metrics, decisions,
output _length_ — is POSTed to `<url>/run` after the ledger and run-card are written.

- **Push-only.** `uplink.py` contains no download path, so a hub cannot inject content
  into a repo's context.
- **Never in the critical path.** Unreachable, refused or HTTP-erroring hubs degrade to a
  printed status line; a hub cannot fail a run or change its verdict.
- `doctor` validates the value without touching the network.

### `agent-dispatch` flow (mandarin pilot)

1. `solar-governor run "<task>" --repo <path>` → graph routes to a role
   (registry) and writes `.solar/handoffs/<role>-attempt1-*.md`.
2. It interrupts: open the repo in VS Code Copilot, run that `.agent.md`
   specialist (its model = DeepSeek via the extension) with the handoff's
   Objective.
3. Paste the agent's result back (or save it and type the path) → the graph
   resumes → review → complete → ledger + run-card.
4. Non-interactive: `solar-governor run "<task>" --result "<text|path>"`.

### `--json` step contract (agent-driven UI — v4-like UX on a graph core)

`run --json` executes **one graph step** and returns a machine-readable JSON doc
with a distinct exit code, so a thin driver agent (the UI entry point) can run,
interrupt, dispatch a specialist, and resume — instead of a human babysitting
stdin. The graph/runners underneath stay provider-agnostic.

```bash
# start a new thread (or step an empty one):
solar-governor run "<task>" --repo <path> --thread <t> --json
# resume a paused thread (task string identical; state comes from checkpoint):
solar-governor run "<task>" --repo <path> --thread <t> --json --result "<file|text>"   # agent-dispatch
solar-governor run "<task>" --repo <path> --thread <t> --json --approve approve|deny    # review
```

| Exit | Meaning                                                               | JSON `status`                                                |
| ---- | --------------------------------------------------------------------- | ------------------------------------------------------------ |
| `0`  | run complete                                                          | `complete` — stage/verdict/role/output/run_card              |
| `10` | paused: run the specialist, then `--result`                           | `interrupt` kind=`agent-dispatch` — role/attempt/handoff/ask |
| `11` | paused: ask the human, then `--approve`                               | `interrupt` kind=`review` — role/ask                         |
| `2`  | usage/state error (e.g. resume on a thread with no pending interrupt) | `error` — message                                            |

A paused thread is detected via the SQLite checkpoint; `run --json` refuses to
plain-invoke a paused thread (that would resume with the wrong value). Ledger +
run-card are (re)written at every step, so progress is on disk even mid-pause.

A driver agent (`@Governor v5`, see the repo's `.github/agents/`) loops on these
exit codes: exit 10 → read the handoff, run the matching `.agent.md` specialist
(via `runSubagent`), save its answer to `<handoff>.result.md`, resume with that
path; exit 11 → ask the user approve/deny and resume with `--approve`.

## What it proves now

- Light graph: `MATERIAL_GATE → DISPATCH → SPECIALIST → REVIEW(cond) → COMPLETE`
  with a bounded rework loop (≤3).
- Registry-aware routing: repo roles (e.g. mandarin's frontend-engineer) win over
  generic defaults when their name appears in the task.
- SQLite checkpoint (durable, resume by thread_id) + interrupt-over-CLI when
  `human_approval` is on.
- Runner abstraction: `agent-dispatch` (IDE handoff) · `http` · `stub`.
- Ledger (`record`) appends one section per run and never rewrites content it did not
  write; run-card JSON per run at `.solar/runs/<thread>.json` (tokens, verdict, model,
  decisions).
- Ledger render (human view from state).

## Test

```bash
python -m pytest tests/           # 165 tests: graph, routing, ledger, executor, server,
                                  # workspace guards, command vocabulary + approval gate,
                                  # tool-loop termination, runner selection, uplink,
                                  # doctor + eval case resolution, install surface
python tests/test_smoke.py        # smoke only
```
