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


def role_keys(registry: dict) -> list[str]:
    """Role keys only (a real role spec carries a `system` prompt; structural
    keys such as 'chains' and 'playbooks' — whose entries may also carry a
    'role' slot — are excluded)."""
    return [k for k, v in registry.items() if isinstance(v, dict) and "system" in v]


def declared(registry_path: Path | None = None) -> list[str]:
    """Role keys the REPO's own file declares, before the built-ins are merged in.

    `load` merges, so its role count is what can be DISPATCHED, not what the repo
    wrote — a distinction that reads as a defect when it is only unsaid (`doctor`
    reported "10 specialists" for a repo that declares 7). Reported, not merged:
    the count has to come from the file, not from the union.
    """
    if not (registry_path and registry_path.exists()):
        return []
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception:
        return []                       # unreadable file: say nothing, do not guess
    return role_keys(data) if isinstance(data, dict) else []


def chains(registry_path: Path | None = None) -> dict:
    """Named chains (data): name -> ordered list where a nested list = a parallel group.

    Example:
      {"epic": ["investigator", "architect",
                ["frontend-engineer", "backend-engineer"],
                "docs-writer", "code-reviewer"]}
    """
    reg = load(registry_path)
    return reg.get("chains") or {}


def chain_entry(chains_map: dict, name: str) -> str:
    """First role of a named chain (the role the governor kicks off)."""
    raw = chains_map.get(name)
    if not raw:
        raise KeyError(f"no chain '{name}' in registry (have: {sorted(chains_map)})")
    first = raw[0]
    return first[0] if isinstance(first, list) else first


def chain_text(chains_map: dict, name: str) -> str:
    """Human-readable form of a chain for the handoff (parallel group in parens)."""
    raw = chains_map.get(name)
    if not raw:
        raise KeyError(f"no chain '{name}' in registry (have: {sorted(chains_map)})")
    parts = []
    for item in raw:
        parts.append(" + ".join(item) if isinstance(item, list) else item)
    return " -> ".join(parts)
