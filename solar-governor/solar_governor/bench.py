"""solar-governor bench: run the same task N times and aggregate the numbers.

Headless path for measurable telemetry (v5 §10 operational eval slice). Requires
the `http` runner (an API key in the environment + config runner `http`), so
token + duration numbers are real (the model call is in-process). Each run is a
fresh thread; results are printed as a table and returned as a dict.

    solar-governor bench --repo <path> --task "<objective>" --n 5 [--role X]

WHAT THE NUMBERS MEAN (TD-5.7-6). `bench` measures **cost and duration**: tokens
in/out, wall time, tool calls. It does not measure whether the answer was right.
`approved` counts the runs that reached `stage=complete` with `verdict=APPROVED`,
and with `human_approval: false` that verdict is the graph approving *itself* — so
a wrong answer is approved too (measured: `2/2` while the model answered one of
three questions wrong). Correctness is graded by `eval`, against a known-answer
battery. The count is named `approved` rather than `passed` for that reason: a
number that reads as a score gets acted on as one.

Nothing here is inferred. Every repetition writes a run-card (`.solar/runs/`), and
every row carries the answer with its length and hash, so the table can be checked
against an artefact instead of trusted. Before v5.7.3 the two agreed only by
coincidence: `.solar/runs/` stayed empty and the answers were unrecoverable.
"""
from __future__ import annotations

import argparse
import hashlib
import statistics
import time
from pathlib import Path

from . import executor, runcard
from .core import Config
from .graph import run_task

# Printed wherever the count is printed. The number is otherwise read as a score,
# which is exactly what the "2/2 passed" measurement was: an approval read as a result.
APPROVED_IS_NOT_CORRECT = (
    "approved = stage=complete + verdict=APPROVED, which the graph grants itself when "
    "human_approval is false. It is not a check of the answer — grade answers with "
    "`solar-governor eval`.")


def run(repo: str, task: str, n: int = 3, role: str = "", chain: str = "") -> dict:
    if n < 1:
        raise SystemExit("bench needs --n >= 1 (an aggregate over no runs is not a number)")
    cfg = Config.load(Path(repo).expanduser().resolve() / ".solar" / "config.json")
    runner = executor.select_runner(cfg.runner, executor.target_for(cfg))
    if runner != "http":
        raise SystemExit(f"bench requires runner=http (resolved: {runner}) — "
                         f"set SOLAR_API_KEY, declare a provider, or set the config's "
                         f"runner to 'http'")

    stamp = int(time.time())
    rows = []
    for i in range(n):
        thread = f"bench-{stamp}-{i}"
        started = time.time()
        try:
            state = run_task(cfg, task, thread=thread, approve="approve",
                             chain=chain or "", role=role or "")
            # The card is the evidence. Without it the table reported numbers that
            # nothing on disk backed, which is the defect class the v5.6.x/v5.7.x
            # releases were about: a report that reads as something it is not.
            card = runcard.write(cfg, state, thread, started)
            out = state.get("output") or ""
            rows.append({
                "i": i, "stage": state.get("stage"), "verdict": state.get("verdict"),
                "role": state.get("role"), "model": state.get("model", "stub"),
                "attempts": state.get("attempts", 0),
                "tokens_in": state.get("tokens_in", 0),
                "tokens_out": state.get("tokens_out", 0),
                "tool_calls": state.get("tool_calls", 0),
                "error": state.get("error") or "",
                "duration_ms": int((time.time() - started) * 1000),
                # The answer itself, so two runs can be COMPARED rather than counted —
                # which is the whole point of a local-vs-cloud bench.
                "output": out,
                "output_chars": len(out),
                "output_sha256": _sha256(out),
                "run_card": str(card),
            })
        except Exception as e:  # pragma: no cover - network/provider failure
            rows.append({"i": i, "stage": "error", "verdict": "",
                         "role": role, "model": runner, "attempts": 0,
                         "tokens_in": 0, "tokens_out": 0, "tool_calls": 0,
                         "error": str(e),
                         "duration_ms": int((time.time() - started) * 1000),
                         "output": "", "output_chars": 0, "output_sha256": "",
                         "run_card": ""})

    approved = [r for r in rows if r["stage"] == "complete" and r["verdict"] == "APPROVED"]
    agg = {
        "n": n, "task": task,
        "approved": len(approved), "not_approved": n - len(approved),
        "role": role or (rows[0]["role"] if rows else ""),
        "models": sorted({r["model"] for r in rows}),
        "avg_tokens_in": _mean(r["tokens_in"] for r in rows if not r["error"]),
        "avg_tokens_out": _mean(r["tokens_out"] for r in rows if not r["error"]),
        "total_tokens": sum(r["tokens_in"] + r["tokens_out"] for r in rows),
        "avg_tool_calls": _mean(r["tool_calls"] for r in rows if not r["error"]),
        "avg_duration_ms": _mean(r["duration_ms"] for r in rows),
        "errors": [r["error"] for r in rows if r["error"]][:3],
        "cards": [r["run_card"] for r in rows if r["run_card"]],
        # Returned, not just printed: the rows ARE the measurement, and a caller that
        # gets aggregates alone cannot tell two different answers apart.
        "rows": rows,
    }
    _print(rows, agg)
    return agg


def _sha256(text: str) -> str:
    """A short, stable fingerprint. Length says "it changed"; this says "same answer"."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _mean(vals):
    vals = list(vals)
    return round(statistics.mean(vals), 1) if vals else 0.0


def _print(rows, agg) -> None:
    models = ", ".join(agg["models"]) or "-"
    print(f"bench: {agg['role'] or '(auto)'} | {agg['approved']}/{agg['n']} approved | "
          f"model {models} | "
          f"avg tok in {agg['avg_tokens_in']} · out {agg['avg_tokens_out']} · "
          f"tools {agg['avg_tool_calls']} · {agg['avg_duration_ms']} ms")
    for r in rows:
        err = f"  ERROR {r['error'][:60]}" if r["error"] else ""
        evidence = f"out {r['output_chars']}ch" + (
            f"/{r['output_sha256'][:8]}" if r["output_sha256"] else "")
        preview = " ".join(r["output"].split())[:60]
        print(f"  #{r['i']} {r['stage']}/{r['verdict']}  in {r['tokens_in']} out "
              f"{r['tokens_out']} tools {r['tool_calls']} {r['duration_ms']}ms "
              f"{evidence}  out: {preview}{err}")
    print(f"  {APPROVED_IS_NOT_CORRECT}")
    if agg["cards"]:
        print(f"  cards: {len(agg['cards'])} written to {Path(agg['cards'][0]).parent}")


def main() -> None:
    ap = argparse.ArgumentParser(prog="solar-governor.bench")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--task", required=True)
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--role", default="")
    ap.add_argument("--chain", default="")
    args = ap.parse_args()
    run(args.repo, args.task, args.n, args.role, args.chain)


if __name__ == "__main__":
    main()
