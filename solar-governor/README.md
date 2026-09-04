# solar-governor — SOLAR-Ralph v5 runtime

The LangGraph control layer for SOLAR v5 (governor-as-graph). Small, installable,
repo-bounded. See `../docs/versions/v5.md` for the full design.

## Status

Implementing — v5.3 track (implement → install on a mandarin branch →
non-invasive tests → merge → pilot epic 25). Currently: light-profile graph
end-to-end with SQLite checkpoint + CLI + doctor + **model executor + workspace
tool + run-cards**. Mandarin's 8 agents are wired as its `SPECIALISTS` registry
on branch `solar-v5-wire`. Next: real-model pilot run + merge.

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

## Model executor (real runs)

The specialist node calls a model through an **OpenAI-compatible** client
(provider-neutral). Configure at runtime via environment — never stored in
files, never committed:

```bash
$env:SOLAR_API_KEY  = "<your deepseek/openrouter key>"   # or DEEPSEEK_API_KEY
$env:SOLAR_BASE_URL = "https://api.deepseek.com"          # default; any OpenAI-compatible host
$env:SOLAR_MODEL    = "deepseek-chat"                     # or cfg.model
```

No key set → deterministic **stub** executor (structure tests stay offline). The
executor offers repo-bounded workspace tools (list_tree / read_file / glob /
write_file) that refuse to escape the repo root.

## What it proves now

- Light graph: `MATERIAL_GATE → DISPATCH → SPECIALIST → REVIEW(cond) → COMPLETE`
  with a bounded rework loop (≤3).
- Registry-aware routing: repo roles (e.g. mandarin's frontend-engineer) win over
generic defaults when their name appears in the task.
- SQLite checkpoint (durable, resume by thread_id) + interrupt-over-CLI when
  `human_approval` is on.
- Model executor (stub offline / real when `SOLAR_API_KEY` set) + workspace tools.
- Run-card JSON per run at `.solar/runs/<thread>.json` (tokens, verdict, model).
- Ledger render (human view from state).

## Test

```bash
python tests/test_smoke.py        # smoke: graph + routing + ledger
python tests/test_executor.py     # executor + workspace guard tests
# or: python -m pytest tests/
```
