"""solar-governor eval: known-answer battery over the http runner.

Deterministic quality signal for tuning — unlike auto-APPROVED verdicts (which
can rubber-stamp an error), each case has a known-good answer checked against
the model's final output via must_contain / not_contain substrings.

Cases are read-only and repo-grounded (mandarin defaults below). Override the
battery with --cases <file.json>:

    [{"id": "...", "role": "...", "objective": "...",
      "must_contain": ["..."], "not_contain": ["..."]}]

Run:  solar-governor eval --repo <path> [--n 3] [--id <case>]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from . import executor
from .core import Config
from .graph import run_task

# DeepSeek-chat list prices (USD per 1M tokens, approx; cache-miss prompt rate)
IN_PER_M = 0.27
OUT_PER_M = 1.10

DEFAULT_CASES: list[dict] = [
    {"id": "shared-entries", "role": "investigator",
     "objective": "Use your read tools to list the top-level entries under "
                  "apps/frontend/src/shared and reply with the directory names only.",
     "must_contain": ["api", "components", "hooks", "store", "utils"]},
    {"id": "chengyu-phase", "role": "investigator",
     "objective": "Read apps/frontend/src/router/LearnRoutes.tsx and its shared "
                  "constants, then reply with the requiredPhase number the chengyu "
                  "route is gated to (just the number).",
     "must_contain": ["4"]},
    {"id": "learn-route-count", "role": "investigator",
     "objective": "How many Learn content routes are data-driven gated in "
                  "LearnRoutes.tsx? Reply with just the number.",
     "must_contain": ["6"]},
    {"id": "guest-badge-testid", "role": "investigator",
     "objective": "Does AppTopBar render a passive Guest identity badge? Find its "
                  "data-testid and reply with the testid value.",
     "must_contain": ["guest-identity-badge"]},
    {"id": "tts-guard", "role": "investigator",
     "objective": "Which auth guard class is applied to the POST /v1/tts route? "
                  "Reply with the guard class name.",
     "must_contain": ["optionalauthguard"]},
    {"id": "cn-join", "role": "investigator",
     "objective": "Read apps/frontend/src/shared/utils/cn.ts and reply with what "
                  "cn('a', null, false, 'b') returns (the exact string).",
     "must_contain": ["a b"]},
]


def check(output: str, case: dict) -> bool:
    low = (output or "").lower()
    must = [c.lower() for c in case.get("must_contain", [])]
    notc = [c.lower() for c in case.get("not_contain", [])]
    return all(c in low for c in must) and not any(c in low for c in notc)


def run(repo: str, cases: list[dict] | None = None, n: int = 1,
        only: str | None = None) -> dict:
    cfg = Config.load(Path(repo).expanduser().resolve() / ".solar" / "config.json")
    runner = executor.select_runner(cfg.runner)
    if runner == "agent-dispatch":
        raise SystemExit("eval requires runner=http|stub (agent-dispatch needs the IDE)")

    stamp = int(time.time())
    rows: list[dict] = []
    for case in (cases or DEFAULT_CASES):
        if only and case["id"] != only:
            continue
        for i in range(n):
            thread = f"eval-{case['id']}-{stamp}-{i}"
            started = time.time()
            try:
                state = run_task(cfg, case["objective"], thread=thread,
                                 approve="approve", role=case["role"])
                out = state.get("output") or ""
                err = state.get("error") or ""
                ok = (state.get("stage") == "complete"
                      and state.get("verdict") == "APPROVED"
                      and not err and check(out, case))
                rows.append({
                    "id": case["id"], "role": case["role"], "pass": ok,
                    "tokens_in": state.get("tokens_in", 0),
                    "tokens_out": state.get("tokens_out", 0),
                    "tool_calls": state.get("tool_calls", 0),
                    "duration_ms": int((time.time() - started) * 1000),
                    "error": err, "output": out[:160],
                })
            except Exception as e:  # pragma: no cover - provider failure
                rows.append({"id": case["id"], "role": case["role"], "pass": False,
                             "tokens_in": 0, "tokens_out": 0, "tool_calls": 0,
                             "duration_ms": int((time.time() - started) * 1000),
                             "error": str(e), "output": ""})

    passed = sum(1 for r in rows if r["pass"])
    total_in = sum(r["tokens_in"] for r in rows)
    total_out = sum(r["tokens_out"] for r in rows)
    agg = {
        "cases": len(rows), "passed": passed, "failed": len(rows) - passed,
        "pass_rate": round(passed / len(rows), 3) if rows else 0.0,
        "total_tokens_in": total_in, "total_tokens_out": total_out,
        "est_cost_usd": round((total_in / 1e6) * IN_PER_M + (total_out / 1e6) * OUT_PER_M, 4),
        "total_duration_ms": sum(r["duration_ms"] for r in rows),
        "rows": rows,
    }
    _print(agg)
    return agg


def _print(agg: dict) -> None:
    print(f"eval: {agg['passed']}/{agg['cases']} passed ({agg['pass_rate']*100:.0f}%) · "
          f"tok in {agg['total_tokens_in']} · out {agg['total_tokens_out']} · "
          f"est ${agg['est_cost_usd']} · {agg['total_duration_ms']} ms")
    for r in agg["rows"]:
        mark = "PASS" if r["pass"] else "FAIL"
        err = f"  err={r['error'][:50]}" if r["error"] else ""
        print(f"  [{mark}] {r['id']:<20} in {r['tokens_in']:>7} out {r['tokens_out']:>5} "
              f"tools {r['tool_calls']:>2} {r['duration_ms']:>6}ms{err}  out: {r['output'][:60]}")


def main() -> None:
    ap = argparse.ArgumentParser(prog="solar-governor.eval")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--cases", default=None, help="path to a JSON cases file")
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--id", default=None, help="run a single case by id")
    args = ap.parse_args()
    cases = None
    if args.cases:
        cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    run(args.repo, cases=cases, n=args.n, only=args.id)


if __name__ == "__main__":
    main()
