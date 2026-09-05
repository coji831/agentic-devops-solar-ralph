"""Tests for named-chain resolution + single-link dispatch (driver-orchestrated).

A named chain in the registry is data: name -> ordered list, where a nested
list = a parallel group. Chains are run by the DRIVER (`--chain <name> --auto`
headless, or the Governor agent per-link `--role` in the IDE) — a bare
`--chain` is rejected. Here we verify: role_keys skips the 'chains' key, chain
resolution/parallel text, entry routing, and that a dispatch handoff carries
chain context but NEVER the falsified "CHAIN ENTRY / run the rest yourself"
instruction.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solar_governor import registry                      # noqa: E402
from solar_governor.core import Config                   # noqa: E402
from solar_governor.graph import run_task                # noqa: E402

CHAIN_REG = {
    "architect": {"role": "Architect", "system": "You plan.", "tools": [],
                  "next_edges": [], "model": ""},
    "investigator": {"role": "Investigator", "system": "You research.", "tools": [],
                     "next_edges": [], "model": ""},
    "chains": {"epic": ["investigator", "architect",
                        ["frontend-engineer", "backend-engineer"],
                        "docs-writer", "code-reviewer"],
                 "mini": ["implementer", "reviewer"]},
}


def _tmp_repo() -> Path:
    r = Path(tempfile.mkdtemp(prefix="solar-chain-"))
    (r / ".solar").mkdir(parents=True)
    (r / ".solar" / "registry.json").write_text(json.dumps(CHAIN_REG), encoding="utf-8")
    return r


def test_role_keys_skip_structural():
    reg = registry.load(None)
    assert "chains" not in reg
    reg2 = registry.load(Path(tempfile.mkdtemp()) / "x.json") if False else None
    # repo registry with a chains key: role_keys must not include it
    r = _tmp_repo()
    merged = registry.load(r / ".solar" / "registry.json")
    assert "chains" in merged
    keys = registry.role_keys(merged)
    assert "investigator" in keys and "architect" in keys
    assert "chains" not in keys
    shutil.rmtree(r)


def test_chain_resolution():
    cm = registry.chains(None)  # generic: no chains
    assert cm == {}
    r = _tmp_repo()
    cm = registry.chains(r / ".solar" / "registry.json")
    assert registry.chain_entry(cm, "epic") == "investigator"
    assert registry.chain_text(cm, "epic") == ("investigator -> architect -> "
                                               "frontend-engineer + backend-engineer -> "
                                               "docs-writer -> code-reviewer")
    try:
        registry.chain_entry(cm, "missing")
        raise AssertionError("expected KeyError")
    except KeyError:
        pass
    shutil.rmtree(r)


def test_run_chain_routes_to_entry_and_marks_handoff():
    """agent-dispatch chain run: graph routes to chain[0] (investigator) as ONE
    link; the handoff carries neutral chain context, NOT a CHAIN-ENTRY/self-run
    instruction (driver-orchestrated model)."""
    r = _tmp_repo()
    cfg = Config(repo=str(r), runner="agent-dispatch")
    cfg.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    state = run_task(cfg, "secure guest identity (epic 25)", thread="c1",
                     chain="epic", resume_result="investigated; deliverable returned")
    assert state.get("stage") == "complete"
    assert state.get("role") == "investigator"      # chain entry, not a classify guess
    assert state.get("chain") == "epic"
    assert state.get("model", "").startswith("agent-dispatch")
    hdir = r / ".solar" / "handoffs"
    handoffs = list(hdir.glob("investigator-attempt1-*.md"))
    assert handoffs, "expected an investigator handoff"
    text = handoffs[0].read_text(encoding="utf-8")
    assert "Chain context" in text and "epic" in text
    assert "CHAIN ENTRY" not in text                 # never tell a link to self-run
    assert "coordinator" in text.lower()
    shutil.rmtree(r)


def test_run_chain_entry_with_parallel_group_text():
    """chain_text renders a parallel group with ' + ' so the entry agent sees it."""
    r = _tmp_repo()
    cm = registry.chains(r / ".solar" / "registry.json")
    assert "frontend-engineer + backend-engineer" in registry.chain_text(cm, "epic")
    shutil.rmtree(r)


def test_run_pinned_role_skips_classify():
    """--role pins dispatch to one role regardless of task wording (Hermes decision)."""
    r = _tmp_repo()
    cfg = Config(repo=str(r), runner="agent-dispatch")
    cfg.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    # task says 'investigate' but we pin to architect -> dispatch must honour the pin
    state = run_task(cfg, "review the login screen", thread="r1", chain="",
                     role="architect", resume_result="architecture pinned run done")
    assert state.get("role") == "architect"
    assert state.get("stage") == "complete"
    shutil.rmtree(r)


def test_role_pin_invalid_role_falls_back():
    """A pinned role that is not in the registry is ignored (falls back to classify)."""
    r = _tmp_repo()
    cfg = Config(repo=str(r), runner="agent-dispatch")
    cfg.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    state = run_task(cfg, "review the login screen", thread="r2", role="ghost-role",
                     resume_result="x")
    # 'ghost-role' not in registry -> classify sees no repo role keyword for this task,
    # generic 'review' keyword wins -> reviewer
    assert state.get("role") == "reviewer"
    shutil.rmtree(r)


def test_chain_auto_runner_on_stub():
    """run_chain runs each link headless in order over the stub runner (offline)."""
    from solar_governor.chain import run_chain
    r = _tmp_repo()
    cfg = Config(repo=str(r), runner="stub")
    cfg.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    agg = run_chain(cfg, "mini", "add a small feature", thread="ca")
    assert agg["chain"] == "mini"
    assert agg["passed"] == 2 and agg["failed"] == 0
    roles = [l["link"] for l in agg["links"]]
    assert roles == ["implementer", "reviewer"]
    # one run-card per link was written
    assert (r / ".solar" / "runs" / "ca-0.json").exists()
    assert (r / ".solar" / "runs" / "ca-1.json").exists()
    shutil.rmtree(r)


def test_executor_error_is_not_auto_approved():
    """An executor failure must end REJECTED (terminal), never a false APPROVED."""
    import solar_governor.executor as ex
    r = _tmp_repo()
    cfg = Config(repo=str(r), runner="http")
    cfg.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    orig = ex.run
    ex.run = lambda *a, **k: {"output": "boom", "usage": {"in": 1, "out": 1},
                              "tool_calls": 0, "error": "provider down", "model": "http"}
    try:
        state = run_task(cfg, "do a thing", thread="er1")
    finally:
        ex.run = orig
    assert state.get("verdict") == "REJECTED", "error output must not auto-approve"
    assert state.get("stage") == "complete"
    assert "provider down" in (state.get("error") or "")
    shutil.rmtree(r)


if __name__ == "__main__":
    for fn in (test_role_keys_skip_structural, test_chain_resolution,
               test_run_chain_routes_to_entry_and_marks_handoff,
               test_run_chain_entry_with_parallel_group_text,
               test_run_pinned_role_skips_classify,
               test_role_pin_invalid_role_falls_back,
               test_chain_auto_runner_on_stub,
               test_executor_error_is_not_auto_approved):
        fn()
        print(f"PASS {fn.__name__}")
    print("all chain tests passed")
