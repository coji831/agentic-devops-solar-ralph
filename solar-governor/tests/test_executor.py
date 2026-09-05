"""Tests for the model executor + workspace tool (v5 §3/§6 + tool layer).

No network: these tests force a key-less environment so the executor falls back
to the stub regardless of whether SOLAR_API_KEY is set on the dev machine.
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

# make these tests deterministic-offline even when a real key is set in the env
os.environ.pop("SOLAR_API_KEY", None)
os.environ.pop("DEEPSEEK_API_KEY", None)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solar_governor import executor               # noqa: E402
from solar_governor.core import Config            # noqa: E402
from solar_governor.graph import build_graph, run_task  # noqa: E402
from solar_governor.workspace import Workspace    # noqa: E402


def _tmp_repo() -> Path:
    r = Path(tempfile.mkdtemp(prefix="solar-exec-"))
    (r / "apps").mkdir(parents=True)
    (r / "apps" / "a.test.ts").write_text("export const x = 1;\n", encoding="utf-8")
    (r / ".git").mkdir()
    return r


def _cfg(repo: Path) -> Config:
    cfg = Config(repo=str(repo))
    cfg.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    return cfg


def test_executor_stub_when_no_key():
    assert executor.available() is False   # no key in CI/offline env
    res = executor.run("implementer", "You are an implementer.", "add a feature",
                       Path(tempfile.gettempdir()))
    assert res.get("model") == "stub"
    assert "add a feature" in res.get("output", "")
    assert res.get("usage") == {"in": 0, "out": 0}


def test_workspace_list_and_read():
    r = _tmp_repo()
    ws = Workspace(r)
    tree = ws.list_tree()
    assert "a.test.ts" in tree
    content = ws.read_file("apps/a.test.ts")
    assert "export const x" in content
    shutil.rmtree(r)


def test_workspace_confinement_blocks_escape():
    r = _tmp_repo()
    ws = Workspace(r)
    # write_file must refuse a path that resolves outside the repo
    result = ws.write_file("../../escape.txt", "boom")
    assert result.startswith("ERROR")
    assert not (r.parent / "escape.txt").exists()
    shutil.rmtree(r)


def test_workspace_write_roundtrip():
    r = _tmp_repo()
    ws = Workspace(r)
    assert ws.write_file("apps/b.ts", "export const y = 2;\n").startswith("wrote")
    assert (r / "apps" / "b.ts").exists()
    shutil.rmtree(r)


def test_graph_routes_repo_role_from_registry():
    r = _tmp_repo()
    reg = {"frontend-engineer": {"role": "Frontend Engineer",
                                 "system": "You build frontend.", "tools": [],
                                 "next_edges": [], "model": ""}}
    (r / ".solar").mkdir(parents=True)
    (r / ".solar" / "registry.json").write_text(json.dumps(reg), encoding="utf-8")
    from solar_governor.graph import _classify
    assert _classify("build a frontend-engineer login screen", reg) == "frontend-engineer"
    shutil.rmtree(r)


def test_select_runner_auto_and_explicit():
    assert executor.select_runner("") in ("http", "stub")   # no key -> stub
    assert executor.select_runner("agent-dispatch") == "agent-dispatch"
    assert executor.select_runner("http") == "http"
    assert executor.select_runner("stub") == "stub"


def test_handoff_written_and_resolve():
    r = _tmp_repo()
    path = executor.write_handoff("frontend-engineer", "You build frontend.",
                                  "add a login screen", r, attempt=1)
    assert path.exists()
    assert "frontend-engineer" in path.name
    text = path.read_text(encoding="utf-8")
    assert "add a login screen" in text
    # resolve_result returns pasted text as-is
    assert executor.resolve_result("done: built it", r) == "done: built it"
    # resolve_result reads a file path if given
    result_file = r / ".solar" / "handoffs" / "result.txt"
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text("the agent result", encoding="utf-8")
    assert executor.resolve_result(str(result_file), r) == "the agent result"
    shutil.rmtree(r)


def test_run_task_agent_dispatch_resumes():
    """agent-dispatch: specialist writes a handoff + interrupts; resume_result
    (non-interactive) supplies the agent's answer as the specialist output."""
    r = _tmp_repo()
    reg = {"frontend-engineer": {"role": "Frontend Engineer",
                                 "system": "You build frontend.", "tools": [],
                                 "next_edges": [], "model": ""}}
    (r / ".solar").mkdir(parents=True)
    (r / ".solar" / "registry.json").write_text(json.dumps(reg), encoding="utf-8")
    cfg = Config(repo=str(r), runner="agent-dispatch")
    cfg.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    state = run_task(cfg, "build a frontend-engineer login screen", thread="ad1",
                     resume_result="added LoginScreen.tsx with tests")
    assert state.get("stage") == "complete"
    assert state.get("output") == "added LoginScreen.tsx with tests"
    assert state.get("model", "").startswith("agent-dispatch")
    # handoff file persisted
    hdir = r / ".solar" / "handoffs"
    assert any(hdir.glob("frontend-engineer-attempt1-*.md"))
    shutil.rmtree(r)


if __name__ == "__main__":
    for fn in (test_executor_stub_when_no_key, test_workspace_list_and_read,
               test_workspace_confinement_blocks_escape, test_workspace_write_roundtrip,
               test_graph_routes_repo_role_from_registry, test_select_runner_auto_and_explicit,
               test_handoff_written_and_resolve, test_run_task_agent_dispatch_resumes):
        fn()
        print(f"PASS {fn.__name__}")
    print("all executor tests passed")
