"""Tests for the model executor + workspace tool (v5 §3/§6 + tool layer).

No network: executor falls back to the stub when SOLAR_API_KEY is unset, so
these run offline. Workspace confinement is tested directly.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solar_governor import executor               # noqa: E402
from solar_governor.core import Config            # noqa: E402
from solar_governor.graph import build_graph      # noqa: E402
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


if __name__ == "__main__":
    for fn in (test_executor_stub_when_no_key, test_workspace_list_and_read,
               test_workspace_confinement_blocks_escape, test_workspace_write_roundtrip,
               test_graph_routes_repo_role_from_registry):
        fn()
        print(f"PASS {fn.__name__}")
    print("all executor tests passed")
