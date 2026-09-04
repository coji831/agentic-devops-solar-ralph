"""Non-invasive smoke tests for solar-governor (no API key, temp repo only).

Run:  python -m pytest tests/test_smoke.py      (or)      python tests/test_smoke.py
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solar_governor.core import Config          # noqa: E402
from solar_governor.graph import build_graph, run_task  # noqa: E402
from solar_governor.ledger import render        # noqa: E402
from solar_governor.registry import load as load_registry  # noqa: E402


def _tmp_repo() -> Path:
    return Path(tempfile.mkdtemp(prefix="solar-gov-"))


def _cfg(repo: Path, approval: bool = False) -> Config:
    cfg = Config(repo=str(repo), human_approval=approval)
    cfg.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.save(repo / ".solar" / "config.json")
    return cfg


def test_graph_compiles():
    repo = _tmp_repo()
    g = build_graph(_cfg(repo))
    assert g is not None
    shutil.rmtree(repo)


def test_run_completes_and_routes_role():
    repo = _tmp_repo()
    cfg = _cfg(repo)
    state = run_task(cfg, "add a login feature with tests", thread="smoke1")
    assert state.get("stage") == "complete"
    assert state.get("verdict") == "APPROVED"
    assert state.get("role") == "tester"          # "tests" keyword routes to tester
    assert any("TASK_COMPLETE" in d for d in state.get("decisions_log", []))
    shutil.rmtree(repo)


def test_run_default_role_implementer():
    repo = _tmp_repo()
    cfg = _cfg(repo)
    state = run_task(cfg, "refactor the API layer", thread="smoke2")
    assert state.get("role") == "implementer"
    shutil.rmtree(repo)


def test_ledger_renders():
    repo = _tmp_repo()
    cfg = _cfg(repo)
    state = run_task(cfg, "ship a small feature", thread="smoke3")
    ledger = render(cfg, state)
    text = ledger.read_text(encoding="utf-8")
    assert "Objective" in text and "TASK_COMPLETE" in text
    shutil.rmtree(repo)


def test_registry_loads():
    reg = load_registry(None)
    assert {"implementer", "tester", "reviewer"} <= set(reg)


if __name__ == "__main__":
    for fn in (test_graph_compiles, test_run_completes_and_routes_role,
               test_run_default_role_implementer, test_ledger_renders, test_registry_loads):
        fn()
        print(f"PASS {fn.__name__}")
    print("all smoke tests passed")
