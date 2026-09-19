"""Run-card writer (v5 §14.7.3): one JSON per task run.

Layered capture: checkpoint = full state (SQLite), run-card = structured
metrics (tokens, duration, verdict, routing). Written to
`.solar/runs/<thread_id>.json` (repo-local, gitignored).
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

# The card is documented as the complete structured record (ledger.py), and it was not:
# neither it nor the ledger section carried the run's OUTPUT, so what a finished run
# concluded was unrecoverable from every artefact on disk — a card that reads as the
# record while missing the answer (TD-5.7-6, found benching a local model).
#
# Capped rather than unbounded, like a read is, with a marker that says so: a truncated
# answer must not read as a short one (v5.7.2's rule, and the reason the cap is named).
MAX_OUTPUT_CHARS = 20_000


def _clip_output(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return (f"{text[:MAX_OUTPUT_CHARS]}…[output elided: {len(text)} chars, "
            f"first {MAX_OUTPUT_CHARS} shown]")


def write(cfg, state: dict, thread: str, started_at: float) -> Path:
    run_dir = cfg.root / ".solar" / "runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"{thread}-{time.strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:6]}"
    card = {
        "run_id": run_id,
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "repo": cfg.root.name,
        "harness": "v5-light",
        "profile": cfg.profile,
        "thread": thread,
        "objective": state.get("objective", ""),
        "role": state.get("role", ""),
        "chain": state.get("chain", ""),
        "outcome": "complete" if state.get("stage") == "complete" else state.get("stage", ""),
        "verdict": state.get("verdict", ""),
        "attempts": state.get("attempts", 0),
        "steps": len(state.get("decisions_log", [])),
        # `reported` is not decoration: an endpoint may omit usage, and 0/0 from a real
        # model is otherwise the same numbers a stub reports (TD-5.6-12).
        "tokens": {"in": state.get("tokens_in", 0), "out": state.get("tokens_out", 0),
                   "reported": bool(state.get("usage_reported", False))},
        "tool_calls": state.get("tool_calls", 0),
        "model": state.get("model", "stub"),
        "provider": state.get("provider", ""),
        "error": state.get("error", ""),
        "forced_final": bool(state.get("forced_final", False)),
        # What the run concluded. Without it `verdict: APPROVED` was the only thing
        # recoverable from a finished run, and a verdict the graph grants itself cannot
        # stand in for the answer (TD-5.7-6).
        "output": _clip_output(state.get("output") or ""),
        # the decisions log lives in the ledger section too, but the structured record
        # has to stand on its own: the ledger is a growing human view, this is the card
        "decisions": list(state.get("decisions_log") or []),
        # TWO CLOCKS (v5.7.4), because they measure different things and only one of them
        # was ever right about the run.
        #
        # `node_ms` is the run's own clock: every node's execution, summed, accumulated
        # through the checkpoint so a run driven step-by-step with `--result` totals all of
        # its steps rather than only the last one. It is NODE time - per-invocation process
        # overhead and any human pause between invocations are outside it, so it is not
        # `duration_ms` and the two are not comparable. `null` when no node was timed - a
        # state built by hand, or a driver's error row - because `0` and "never timed" would
        # be the same digits, the asymmetry `tokens.reported` closes for `0/0` (TD-5.6-12).
        "node_ms": state.get("node_ms"),
        # `duration_ms` is UNCHANGED and means what it always meant to this writer: the wall
        # clock around the invocation that wrote this card. It is kept, not replaced,
        # because it is a real reading of a different thing (the driver's own wait) — and
        # because redefining it would silently rewrite the meaning of every card already on
        # disk. Additive, so this is a patch and not a migration.
        "duration_ms": int((time.time() - started_at) * 1000),
    }
    path = run_dir / f"{thread}.json"
    path.write_text(json.dumps(card, indent=2), encoding="utf-8")
    return path
