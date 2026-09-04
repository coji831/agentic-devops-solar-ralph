"""SPECIALISTS registry (v5 §6) — role -> {system, tools, next_edges, model}.

Generic defaults; a repo installs its own by dropping a `registry.json` at
`.solar/registry.json` (or the CLI converts existing agents). Registry is data:
swap = edit one entry, no wiring changes.
"""
import json
from pathlib import Path

DEFAULT_SPECIALISTS: dict = {
    "implementer": {
        "role": "Implementer",
        "system": "You implement the task precisely and minimally. Verify your work.",
        "tools": ["workspace", "exec"],
        "next_edges": ["review"],
        "model": "",
    },
    "tester": {
        "role": "Tester",
        "system": "You add or repair tests and run the test suite for the task output.",
        "tools": ["workspace", "exec"],
        "next_edges": ["review"],
        "model": "",
    },
    "reviewer": {
        "role": "Reviewer",
        "system": "You review the output adversarially (non-author). Verdict: APPROVED or REJECTED.",
        "tools": ["workspace"],
        "next_edges": ["complete"],
        "model": "",
    },
}


def load(registry_path: Path | None = None) -> dict:
    if registry_path and registry_path.exists():
        data = json.loads(registry_path.read_text(encoding="utf-8"))
        merged = dict(DEFAULT_SPECIALISTS)
        merged.update(data)
        return merged
    return dict(DEFAULT_SPECIALISTS)
