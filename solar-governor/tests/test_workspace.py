"""Dedicated tests for the workspace tool layer (v5 §11 sovereignty guard).

`Workspace` is the repo-bounded read/glob/write surface handed to the model
executor. Three of its behaviours were already covered incidentally by
`test_executor.py`; this file is the full pass — confinement, truncation, the
skip rules, and the schema/handler contract.

No network and no API key: only the tool layer is exercised.

Run:  python -m pytest tests/test_workspace.py   (or)   python tests/test_workspace.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solar_governor.workspace import MAX_READ_CHARS, Workspace  # noqa: E402


def _tmp_repo() -> Path:
    """A small repo-shaped tree: source, a vendored dir, a skipped ext, config."""
    r = Path(tempfile.mkdtemp(prefix="solar-ws-"))
    (r / "apps").mkdir(parents=True)
    (r / "apps" / "a.test.ts").write_text("export const x = 1;\n", encoding="utf-8")
    (r / "apps" / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (r / ".git").mkdir()
    (r / ".solar").mkdir()
    (r / ".solar" / "registry.json").write_text('{"implementer": {}}', encoding="utf-8")
    (r / "node_modules").mkdir()
    (r / "node_modules" / "dep.js").write_text("module.exports = {};\n", encoding="utf-8")
    return r


# --- role spec plumbing -----------------------------------------------------
# Part of the v5.4.0 plumbing: the workspace carries the role's registry entry so
# the write policy and the offered tool set can be derived from the ROLE.

def test_workspace_spec_defaults_to_empty():
    r = _tmp_repo()
    ws = Workspace(r)
    assert ws.spec == {}
    shutil.rmtree(r)


def test_workspace_accepts_a_role_spec():
    r = _tmp_repo()
    spec = {"system": "You review.", "tools": ["workspace"], "model": "deepseek-chat"}
    ws = Workspace(r, spec)
    assert ws.spec["tools"] == ["workspace"]
    assert ws.spec["model"] == "deepseek-chat"
    shutil.rmtree(r)


def test_workspace_spec_is_a_deep_copy():
    """Mutating ws.spec must not reach back into the caller's registry dict."""
    r = _tmp_repo()
    spec = {"tools": ["workspace"]}
    ws = Workspace(r, spec)
    ws.spec["tools"].append("exec")
    assert spec == {"tools": ["workspace"]}
    shutil.rmtree(r)


def test_role_spec_survives_the_graph_to_executor_hop():
    """The WHOLE registry entry must reach the executor (v5.4.0 plumbing).

    `_role_spec` used to return `(role, system)` only, dropping `tools`/`model`
    and every future policy key — so the executor could never derive anything
    from the role. This is the end-to-end proof that it now arrives intact.

    The executor is patched because `run()` returns the stub BEFORE it builds a
    Workspace when no API key is set, which would hide the very hop under test.
    """
    import json as _json

    from solar_governor import executor, graph
    from solar_governor.core import Config

    r = _tmp_repo()
    entry = {"role": "Reviewer", "system": "You review.",
             "tools": ["workspace"], "model": "deepseek-chat"}
    (r / ".solar" / "registry.json").write_text(_json.dumps({"reviewer": entry}),
                                                encoding="utf-8")
    cfg = Config(repo=str(r), runner="stub")

    seen: dict = {}
    orig = executor.run

    def _capture(*a, **k):
        seen.update(k)
        return {"output": "ok", "usage": {"in": 0, "out": 0}}

    executor.run = _capture
    try:
        graph._execute(cfg, {"role": "reviewer", "objective": "audit the change"})
    finally:
        executor.run = orig

    assert seen.get("spec") == entry, "role spec was dropped in transit"
    assert seen.get("system_prompt") == "You review."
    assert seen.get("role") == "reviewer"
    shutil.rmtree(r)


# --- list_tree --------------------------------------------------------------

def test_list_tree_skips_vendored_and_hidden_dirs():
    r = _tmp_repo()
    tree = Workspace(r).list_tree()
    assert "apps" in tree and "a.test.ts" in tree
    assert "node_modules" not in tree      # _SKIP_DIRS
    assert ".git" not in tree              # _SKIP_DIRS
    assert ".solar" not in tree            # _SKIP_DIRS
    shutil.rmtree(r)


def test_list_tree_skips_binary_extensions():
    r = _tmp_repo()
    tree = Workspace(r).list_tree()
    assert "logo.png" not in tree          # _SKIP_EXTS
    shutil.rmtree(r)


def test_list_tree_missing_path_reports_error():
    r = _tmp_repo()
    assert Workspace(r).list_tree("nope").startswith("ERROR")
    shutil.rmtree(r)


# --- read_file --------------------------------------------------------------

def test_read_file_returns_contents_with_header():
    r = _tmp_repo()
    out = Workspace(r).read_file("apps/a.test.ts")
    assert out.startswith("--- apps/a.test.ts ---")
    assert "export const x" in out
    shutil.rmtree(r)


def test_read_file_rejects_a_directory():
    r = _tmp_repo()
    assert Workspace(r).read_file("apps").startswith("ERROR")
    shutil.rmtree(r)


def test_read_file_truncates_above_max_read_chars():
    r = _tmp_repo()
    big = "x" * (MAX_READ_CHARS + 500)
    (r / "big.txt").write_text(big, encoding="utf-8")
    out = Workspace(r).read_file("big.txt")
    assert "[truncated]" in out
    assert len(out) < len(big)             # the cap actually bites
    shutil.rmtree(r)


def test_read_file_escape_raises_value_error():
    """A direct call raises; see the call_tool test for the model-facing path."""
    r = _tmp_repo()
    try:
        Workspace(r).read_file("../../escape.txt")
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "escapes repo root" in str(e)
    shutil.rmtree(r)


# --- glob -------------------------------------------------------------------

def test_glob_matches_and_skips():
    r = _tmp_repo()
    out = Workspace(r).glob("**/*.test.ts")
    assert "apps/a.test.ts" in out
    assert "dep.js" not in out             # under node_modules
    assert "logo.png" not in out           # skipped ext
    shutil.rmtree(r)


def test_glob_no_matches_reports_cleanly():
    r = _tmp_repo()
    assert Workspace(r).glob("**/*.nope") == "(no matches)"
    shutil.rmtree(r)


# --- write_file -------------------------------------------------------------

def test_write_file_creates_parent_dirs_and_reports_size():
    r = _tmp_repo()
    out = Workspace(r).write_file("deep/nested/c.ts", "export const c = 3;\n")
    assert out.startswith("wrote deep/nested/c.ts")
    assert (r / "deep" / "nested" / "c.ts").read_text(encoding="utf-8") == "export const c = 3;\n"
    shutil.rmtree(r)


def test_write_file_refuses_escape():
    """The root-confinement guard must survive on the write path."""
    r = _tmp_repo()
    out = Workspace(r).write_file("../../escape.txt", "boom")
    assert out.startswith("ERROR")
    assert not (r.parent / "escape.txt").exists()
    shutil.rmtree(r)


def test_write_file_refuses_a_directory_target():
    r = _tmp_repo()
    assert Workspace(r).write_file("apps", "clobber").startswith("ERROR")
    shutil.rmtree(r)


def test_write_file_refuses_solar_registry():
    """THE HOLE, now closed: the deny-list is consulted on the write path.

    Root confinement alone left `.solar/registry.json` writable, so an injected
    objective could rewrite the agent's own system prompt with no shell at all.
    This test previously asserted the write SUCCEEDED, as the pre-fix baseline.
    """
    r = _tmp_repo()
    out = Workspace(r).write_file(".solar/registry.json", '{"pwned": {}}')
    assert out.startswith("ERROR: refusing to write")
    assert (r / ".solar" / "registry.json").read_text(encoding="utf-8") == '{"implementer": {}}'
    shutil.rmtree(r)


def test_write_deny_list_covers_dirs_names_and_nesting():
    r = _tmp_repo()
    ws = Workspace(r)
    for rel in (".git/hooks/pre-commit", ".github/workflows/ci.yml",
                ".vscode/settings.json", "apps/.solar/registry.json",
                "package.json", "apps/deep/package.json", "pyproject.toml",
                "Dockerfile", "apps/.mcp.json"):
        assert ws.write_file(rel, "x").startswith("ERROR: refusing"), rel
    shutil.rmtree(r)


def test_write_deny_list_is_case_insensitive():
    """Windows/macOS filesystems are case-insensitive, so the guard must be."""
    r = _tmp_repo()
    assert Workspace(r).write_file(".SOLAR/registry.json", "x").startswith("ERROR: refusing")
    assert Workspace(r).write_file("Package.JSON", "x").startswith("ERROR: refusing")
    shutil.rmtree(r)


def test_write_deny_list_does_not_over_block():
    """Source files, tests and docs must still be writable."""
    r = _tmp_repo()
    ws = Workspace(r)
    for rel in ("apps/b.ts", "apps/b.test.ts", "docs/notes.md", "README.md",
                "src/config.json"):
        assert ws.write_file(rel, "x").startswith("wrote"), rel
    shutil.rmtree(r)


# --- read_file line ranges (Part A) -----------------------------------------

def test_read_file_range_returns_only_that_slice():
    r = _tmp_repo()
    (r / "n.txt").write_text("\n".join(f"L{i}" for i in range(1, 11)) + "\n",
                             encoding="utf-8")
    out = Workspace(r).read_file("n.txt", start=3, end=5)
    assert "[lines 3-5 of 10]" in out
    assert "L3" in out and "L5" in out
    assert "L2" not in out and "L6" not in out
    shutil.rmtree(r)


def test_read_file_range_clamps_to_the_file():
    r = _tmp_repo()
    (r / "n.txt").write_text("\n".join(f"L{i}" for i in range(1, 6)) + "\n",
                             encoding="utf-8")
    out = Workspace(r).read_file("n.txt", start=2, end=999)
    assert "[lines 2-5 of 5]" in out
    out = Workspace(r).read_file("n.txt", end=2)
    assert "[lines 1-2 of 5]" in out
    shutil.rmtree(r)


def test_read_file_range_past_the_end_is_an_error():
    r = _tmp_repo()
    (r / "n.txt").write_text("a\nb\n", encoding="utf-8")
    out = Workspace(r).read_file("n.txt", start=50)
    assert out.startswith("ERROR: empty range")
    shutil.rmtree(r)


def test_read_file_range_bypasses_the_char_truncation():
    """A range is the way to reach past MAX_READ_CHARS in a large file."""
    r = _tmp_repo()
    lines = ["x" * 100 for _ in range(MAX_READ_CHARS // 100 + 200)]
    (r / "big.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    ws = Workspace(r)
    assert "[truncated]" in ws.read_file("big.txt")
    ranged = ws.read_file("big.txt", start=len(lines) - 9, end=len(lines))
    assert "[truncated]" not in ranged
    assert f"of {len(lines)}" in ranged
    shutil.rmtree(r)


def test_read_file_bad_range_type_is_an_error_not_a_crash():
    r = _tmp_repo()
    (r / "n.txt").write_text("a\nb\n", encoding="utf-8")
    assert Workspace(r).read_file("n.txt", start="three").startswith("ERROR")
    shutil.rmtree(r)


# --- schema / handler contract ----------------------------------------------

def test_tool_schemas_shape():
    r = _tmp_repo()
    schemas = Workspace(r).tool_schemas()
    names = {s["function"]["name"] for s in schemas}
    assert names == {"list_tree", "read_file", "glob", "write_file"}
    for s in schemas:
        assert s["type"] == "function"
        assert s["function"]["description"]
        assert s["function"]["parameters"]["type"] == "object"
    shutil.rmtree(r)


def test_read_file_schema_advertises_the_range_params():
    """A parameter ABSENT from the schema is a parameter the model never sees.

    `read_file(rel, start, end)` can work perfectly and still be useless if the
    schema does not advertise start/end — the model has no reason to send them.
    This is the specific way Part A silently does nothing.
    """
    r = _tmp_repo()
    schemas = {s["function"]["name"]: s for s in Workspace(r).tool_schemas()}
    params = schemas["read_file"]["function"]["parameters"]
    assert {"rel", "start", "end"} <= set(params["properties"])
    assert params["required"] == ["rel"]
    shutil.rmtree(r)


def test_every_advertised_tool_has_a_handler():
    """Schema/handler drift guard.

    If a tool is advertised but `call_tool` cannot dispatch it, the model is
    offered something that always errors. Part A adds read_file params, so this
    invariant is worth pinning.
    """
    r = _tmp_repo()
    ws = Workspace(r)
    for s in ws.tool_schemas():
        name = s["function"]["name"]
        assert callable(getattr(ws, name, None)), f"{name} advertised but not implemented"
    shutil.rmtree(r)


def test_call_tool_unknown_tool_reports_error():
    r = _tmp_repo()
    assert Workspace(r).call_tool("nope", {}).startswith("ERROR: unknown tool")
    shutil.rmtree(r)


def test_call_tool_bad_args_reports_error():
    r = _tmp_repo()
    assert Workspace(r).call_tool("read_file", {"nope": 1}).startswith("ERROR")
    shutil.rmtree(r)


def test_call_tool_contains_the_escape_as_an_error_string():
    """The model-facing path must return a string, never raise."""
    r = _tmp_repo()
    out = Workspace(r).call_tool("read_file", {"rel": "../../escape.txt"})
    assert out.startswith("ERROR")
    shutil.rmtree(r)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"all {len(fns)} workspace tests passed")
