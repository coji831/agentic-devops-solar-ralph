# solar-governor — SOLAR-Ralph v5 runtime

The LangGraph control layer for SOLAR v5 (governor-as-graph). Small, installable,
repo-bounded. See `../docs/versions/v5.md` for the full design.

## Status

Implementing — v5.3 track (implement → install on a mandarin branch →
non-invasive tests → merge → pilot epic 25). Currently: light-profile graph
end-to-end with SQLite checkpoint + CLI + doctor + **model executor + workspace
tool + run-cards + `--json` step contract** (for the v4-like UI driver agent).
Mandarin's 8 agents are wired as its `SPECIALISTS` registry on branch
`solar-v5-wire`. Next: real-model pilot run + merge.

## Compatibility with v4 / v5.x

`solar-governor init` writes **`.solar/`** (NEW — runtime state: config.json,
registry.json, `state/` checkpoints, ledger.md) and leaves the **`.github/`**
harness untouched (v4/v5.x agents + hooks coexist; the graph dispatches to them
via the shape-a write adapter). Two different dirs on purpose: `.github/` = the
agent harness, `.solar/` = the v5 graph runtime. v4 users will see a new folder
but nothing moved or broken.

## Commands

```bash
solar-governor init --repo <path> --profile light   # writes .solar/config.json + registry
solar-governor doctor --repo <path>                 # install self-check (PASS/FAIL)
solar-governor run "task description" --repo <path> # run through the graph + ledger + run-card
```

Run without installing: `python -m solar_governor.cli ...` from this directory.

## Runners — how a specialist executes (provider-agnostic)

The graph never calls a provider directly. The SPECIALIST node asks a **runner**
(`cfg.runner`, or env `SOLAR_RUNNER`; default auto = http if a key is set, else
stub):

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

### `http` runner config (env only, never committed)

```bash
$env:SOLAR_API_KEY  = "<your deepseek/openrouter key>"   # or DEEPSEEK_API_KEY
$env:SOLAR_BASE_URL = "https://api.deepseek.com"          # default; any OpenAI-compatible host
$env:SOLAR_MODEL    = "deepseek-chat"                     # or cfg.model
```

Tools (repo-bounded, refuse to escape the repo root): `list_tree` / `read_file` /
`glob` / `write_file`.

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

| Exit | Meaning | JSON `status` |
| ---- | ------- | ------------- |
| `0`  | run complete | `complete` — stage/verdict/role/output/run_card |
| `10` | paused: run the specialist, then `--result` | `interrupt` kind=`agent-dispatch` — role/attempt/handoff/ask |
| `11` | paused: ask the human, then `--approve` | `interrupt` kind=`review` — role/ask |
| `2`  | usage/state error (e.g. resume on a thread with no pending interrupt) | `error` — message |

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
- Run-card JSON per run at `.solar/runs/<thread>.json` (tokens, verdict, model).
- Ledger render (human view from state).

## Test

```bash
python tests/test_smoke.py        # smoke: graph + routing + ledger
python tests/test_executor.py     # executor + workspace guard tests
# or: python -m pytest tests/
```
