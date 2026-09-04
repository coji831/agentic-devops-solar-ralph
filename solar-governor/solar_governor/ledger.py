"""Ledger render (v5 §12): human view derived from final state (checkpoint = source)."""
from pathlib import Path

from .core import Config


def render(cfg: Config, state: dict) -> Path:
    lines = ["## Objective", "", state.get("objective", ""), "",
             "## Work Queue", "",
             "| id | task | role | status | stage |",
             "| --- | --- | --- | --- | --- |"]
    for row in state.get("work_queue", []):
        lines.append(f"| {row.get('id','')} | {row.get('task','')[:50]} | "
                     f"{row.get('role','')} | {row.get('status','')} | {row.get('stage','')} |")
    lines += ["", "## Decisions Log", ""]
    for d in state.get("decisions_log", []):
        lines.append(f"- {d}")
    lines += ["", f"_stage: {state.get('stage','')} · verdict: {state.get('verdict','-')} · "
                  f"attempts: {state.get('attempts',0)}_"]
    cfg.ledger_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.ledger_path.write_text("\n".join(lines), encoding="utf-8")
    return cfg.ledger_path
