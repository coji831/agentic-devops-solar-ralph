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
        # the decisions log lives in the ledger section too, but the structured record
        # has to stand on its own: the ledger is a growing human view, this is the card
        "decisions": list(state.get("decisions_log") or []),
        "duration_ms": int((time.time() - started_at) * 1000),
    }
    path = run_dir / f"{thread}.json"
    path.write_text(json.dumps(card, indent=2), encoding="utf-8")
    return path
