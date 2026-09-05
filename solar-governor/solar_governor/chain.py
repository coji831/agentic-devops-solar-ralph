"""Headless auto chain-runner (driver-orchestrated chaining, no IDE).

Runs a named chain from the registry link-by-link over an in-process runner
(`http` or `stub`), threading each link's output into the next, writing a
run-card per link, and returning per-link + whole-chain metrics.

This is the engine-level version of what the Governor agent does in the IDE:
chain DATA decides the order; this function runs each link reliably. Agents do
NOT need to spawn each other (nested agents lack the tool) — this driver runs
the links. Human-owned gates (UIUX preview) are NOT honoured headless: review
interrupts are auto-approved (pass `approve="approve"`). Use `--json`/HTTP for
gated flows.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from . import executor, runcard
from .core import Config
from .graph import run_task
from .ledger import render
from .registry import load as load_registry

MAX_CONTEXT_PER_LINK = 4000  # chars of prior output threaded forward per link


def _link_objective(objective: str, history: list[str]) -> str:
    if not history:
        return objective
    block = "\n\n## Context from prior chain links\n" + "\n\n".join(history)
    return objective + block[:MAX_CONTEXT_PER_LINK]


def run_chain(cfg: Config, chain_name: str, objective: str,
              thread: str = "chain", approve: str = "approve") -> dict:
    reg = load_registry(cfg.root / ".solar" / "registry.json")
    cm = reg.get("chains") or {}
    raw = cm.get(chain_name)
    if not raw:
        raise KeyError(f"no chain '{chain_name}' in registry (have: {sorted(cm)})")
    runner = executor.select_runner(cfg.runner)
    if runner == "agent-dispatch":
        raise SystemExit("auto chain requires runner=http|stub (agent-dispatch "
                         "needs the IDE; got agent-dispatch)")

    cfg.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    history: list[str] = []
    links: list[dict] = []

    for item in raw:
        roles = item if isinstance(item, list) else [item]
        for role in roles:
            task = _link_objective(objective, history)
            started = time.time()
            try:
                state = run_task(cfg, task, thread=f"{thread}-{len(links)}",
                                 approve=approve, role=role)
                render(cfg, state)
                card = runcard.write(cfg, state, f"{thread}-{len(links)}", started)
                out = (state.get("output") or "").strip()
                row = {
                    "link": role, "stage": state.get("stage"),
                    "verdict": state.get("verdict"), "attempts": state.get("attempts", 0),
                    "tokens_in": state.get("tokens_in", 0),
                    "tokens_out": state.get("tokens_out", 0),
                    "tool_calls": state.get("tool_calls", 0),
                    "model": state.get("model", "stub"),
                    "error": state.get("error") or "",
                    "output": out[:8000],
                    "duration_ms": int((time.time() - started) * 1000),
                    "run_card": str(cfg.root / ".solar" / "runs" / f"{thread}-{len(links)}.json"),
                }
                history.append(f"[{role}] {out[:MAX_CONTEXT_PER_LINK]}")
            except Exception as e:  # pragma: no cover - provider failure
                row = {"link": role, "stage": "error", "verdict": "",
                       "attempts": 0, "tokens_in": 0, "tokens_out": 0,
                       "tool_calls": 0, "model": runner, "error": str(e),
                       "duration_ms": int((time.time() - started) * 1000),
                       "run_card": ""}
            links.append(row)

    ok = [l for l in links if l["stage"] == "complete" and l["verdict"] == "APPROVED"]
    agg = {
        "chain": chain_name, "thread": thread, "date": datetime.now().isoformat(timespec="seconds"),
        "objective": objective, "links": len(links), "passed": len(ok),
        "failed": len(links) - len(ok),
        "total_tokens_in": sum(l["tokens_in"] for l in links),
        "total_tokens_out": sum(l["tokens_out"] for l in links),
        "total_tool_calls": sum(l["tool_calls"] for l in links),
        "total_duration_ms": sum(l["duration_ms"] for l in links),
        "model": links[0]["model"] if links else "",
        "links": links,
    }
    cdir = cfg.root / ".solar" / "chains"
    cdir.mkdir(parents=True, exist_ok=True)
    (cdir / f"{thread}.json").write_text(json.dumps(agg, indent=2, ensure_ascii=False),
                                         encoding="utf-8")
    md = [f"# Chain {chain_name} — {thread}", "",
          f"objective: {objective}", "",
          f"{agg['passed']}/{agg['links']} links passed · tok in {agg['total_tokens_in']} "
          f"· out {agg['total_tokens_out']} · {agg['total_duration_ms']} ms", ""]
    for l in links:
        md += [f"## [{l['link']}] {l['stage']}/{l['verdict']} "
               f"(in {l['tokens_in']} out {l['tokens_out']} tools {l['tool_calls']} "
               f"{l['duration_ms']}ms)", "", l.get("output") or l.get("error") or "", ""]
    (cdir / f"{thread}.md").write_text("\n".join(md), encoding="utf-8")
    return agg


def print_chain(agg: dict) -> None:
    print(f"chain {agg['chain']}  | {agg['passed']}/{agg['links']} links passed | "
          f"tok in {agg['total_tokens_in']} · out {agg['total_tokens_out']} · "
          f"tools {agg['total_tool_calls']} · {agg['total_duration_ms']} ms")
    for l in agg["links"]:
        err = f"  ERROR {l['error'][:60]}" if l["error"] else ""
        print(f"  [{l['link']}] {l['stage']}/{l['verdict']}  in {l['tokens_in']} "
              f"out {l['tokens_out']} tools {l['tool_calls']} {l['duration_ms']}ms{err}")
