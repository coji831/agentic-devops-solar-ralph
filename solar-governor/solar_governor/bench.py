"""solar-governor bench: run the same task N times and aggregate the numbers.

Headless path for measurable telemetry (v5 §10 operational eval slice). Requires
the `http` runner (an API key in the environment + config runner `http`), so
token + duration numbers are real (the model call is in-process). Each run is a
fresh thread; results are printed as a table and returned as a dict.

    solar-governor bench --repo <path> --task "<objective>" --n 5 [--role X]
"""
from __future__ import annotations

import argparse
import statistics
import time

from . import executor
from .core import Config
from .graph import run_task


def run(repo: str, task: str, n: int = 3, role: str = "", chain: str = "") -> dict:
    cfg = Config.load(__import__("pathlib").Path(repo).expanduser().resolve()
                      / ".solar" / "config.json")
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
            rows.append({
                "i": i, "stage": state.get("stage"), "verdict": state.get("verdict"),
                "role": state.get("role"), "model": state.get("model", "stub"),
                "attempts": state.get("attempts", 0),
                "tokens_in": state.get("tokens_in", 0),
                "tokens_out": state.get("tokens_out", 0),
                "tool_calls": state.get("tool_calls", 0),
                "error": state.get("error") or "",
                "duration_ms": int((time.time() - started) * 1000),
            })
        except Exception as e:  # pragma: no cover - network/provider failure
            rows.append({"i": i, "stage": "error", "verdict": "",
                         "role": role, "model": "http", "attempts": 0,
                         "tokens_in": 0, "tokens_out": 0, "tool_calls": 0,
                         "error": str(e), "duration_ms": int((time.time() - started) * 1000)})

    ok = [r for r in rows if r["stage"] == "complete" and r["verdict"] == "APPROVED"]
    agg = {
        "n": n, "passed": len(ok), "failed": n - len(ok),
        "role": role or (ok[0]["role"] if ok else rows[0]["role"]),
        "avg_tokens_in": _mean(r["tokens_in"] for r in rows if not r["error"]),
        "avg_tokens_out": _mean(r["tokens_out"] for r in rows if not r["error"]),
        "total_tokens": sum(r["tokens_in"] + r["tokens_out"] for r in rows),
        "avg_tool_calls": _mean(r["tool_calls"] for r in rows if not r["error"]),
        "avg_duration_ms": _mean(r["duration_ms"] for r in rows),
        "errors": [r["error"] for r in rows if r["error"]][:3],
    }
    _print(rows, agg)
    return agg


def _mean(vals):
    vals = list(vals)
    return round(statistics.mean(vals), 1) if vals else 0.0


def _print(rows, agg) -> None:
    print(f"task: {agg['role'] or '(auto)'}  | {agg['passed']}/{agg['n']} passed | "
          f"avg tok in {agg['avg_tokens_in']} · out {agg['avg_tokens_out']} · "
          f"tools {agg['avg_tool_calls']} · {agg['avg_duration_ms']} ms")
    for r in rows:
        err = f"  ERROR {r['error'][:60]}" if r["error"] else ""
        print(f"  #{r['i']} {r['stage']}/{r['verdict']}  in {r['tokens_in']} out "
              f"{r['tokens_out']} tools {r['tool_calls']} {r['duration_ms']}ms{err}")


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
