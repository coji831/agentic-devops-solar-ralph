# solar-governor — SOLAR-Ralph v5 runtime

The LangGraph control layer for SOLAR v5 (governor-as-graph). Small, installable,
repo-bounded. See `../docs/versions/v5.md` for the full design.

## Status

Implementing — v5.3 track (step 1 of: implement → install on a mandarin branch →
non-invasive tests → merge → pilot epic 25). Currently: light-profile graph
end-to-end with SQLite checkpoint + CLI + doctor + deterministic stub executor.
Model executor + workspace tool = next.

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
solar-governor run "task description" --repo <path> # run through the graph + render ledger
```

Run without installing: `python -m solar_governor.cli ...` from this directory.

## What it proves now

- Light graph: `MATERIAL_GATE → DISPATCH → SPECIALIST → REVIEW(cond) → COMPLETE`
  with a bounded rework loop (≤3).
- Deterministic routing (`classify` → role: implementer/tester).
- SQLite checkpoint (durable, resume by thread_id) + interrupt-over-CLI when
  `human_approval` is on.
- Ledger render (human view from state).
- Stub executor by default (`cfg.model == ""`) — no API key needed for structure
  tests. Real model executor plugs into `graph._execute` (needs workspace MCP +
  provider).

## Test

```bash
python tests/test_smoke.py        # or: python -m pytest tests/test_smoke.py
```
