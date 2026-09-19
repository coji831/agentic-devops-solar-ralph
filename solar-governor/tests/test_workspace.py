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
    """The cap bites, and it says so - by LINE for one enormous line, by FILE for a long file.

    Changed 2026-09-20 with the line numbers: `_clip_line` now runs before the file cap, so a
    single 40k-char line is elided AS A LINE and names its own real length - the more useful
    marker of the two. A file that is long because it has many lines still gets `[truncated]`.
    Neither is silent, which is the property this test exists to hold.
    """
    r = _tmp_repo()
    big = "x" * (MAX_READ_CHARS + 500)
    (r / "big.txt").write_text(big, encoding="utf-8")
    out = Workspace(r).read_file("big.txt")
    assert "elided" in out or "[truncated]" in out
    assert len(out) < len(big)             # the cap actually bites

    (r / "many.txt").write_text("\n".join(f"L{i}" for i in range(20000)), encoding="utf-8")
    many = Workspace(r).read_file("many.txt")
    assert many.startswith("--- many.txt ---\n")
    assert "[truncated]" in many           # the file cap, not the line cap
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


def test_read_file_range_keeps_a_small_slice_byte_identical():
    """The bound must not touch the ordinary case - no marker, no note, and only the prefix added.

    Changed 2026-09-20: every returned line now carries its 1-based number, padded to the FILE's
    width, so ` 3| ` here rather than `3| `. Nothing else moved - a small slice is still returned
    whole, with no elision marker and no `[capped]` note.
    """
    r = _tmp_repo()
    (r / "n.txt").write_text("\n".join(f"L{i}" for i in range(1, 11)) + "\n",
                             encoding="utf-8")
    out = Workspace(r).read_file("n.txt", start=3, end=5)
    assert out == "--- n.txt [lines 3-5 of 10] ---\n 3| L3\n 4| L4\n 5| L5"
    shutil.rmtree(r)


def test_read_file_numbers_every_line_so_a_reader_can_cite_one():
    """The whole-file path is numbered too, and the width comes from the FILE, not the read.

    This is the contract `investigator` needs on the `http` runner: its evidence is `path:line`,
    and this tool is the only way it can read a file there. Padded to the file's width so line 2
    and line 200 read consistently across two reads of one file.
    """
    r = _tmp_repo()
    (r / "n.txt").write_text("\n".join(f"L{i}" for i in range(1, 101)), encoding="utf-8")
    out = Workspace(r).read_file("n.txt")
    body = out.split("\n", 1)[1].splitlines()
    assert body[0] == "  1| L1"            # width 3, from the 100 lines in the file
    assert body[1] == "  2| L2"
    assert body[99] == "100| L100"
    shutil.rmtree(r)


def test_read_file_range_is_bounded_when_one_line_is_enormous():
    """THE DEFECT (TD-5.7-5), as measured: a range bounds LINES, not CHARS.

    A 282,604-char single line — `.tsbuildinfo`, minified JS, a lockfile, a one-line data
    blob — made `read_file(rel, 1, 60)` return 282,669 chars, about 70k tokens, into a 16k
    window. The whole-file path was capped; the ranged path was not, because its docstring
    assumed a line range is a size bound.
    """
    r = _tmp_repo()
    (r / "blob.json").write_text("x" * 282_604, encoding="utf-8")
    out = Workspace(r).read_file("blob.json", start=1, end=60)
    assert len(out) < 5_000, f"range returned {len(out)} chars for a 1-line file"
    # Bounded AND honest: the model is told a line was elided, which line, and how long it was.
    assert "line 1 elided: 282604 chars" in out
    assert out.startswith("--- blob.json [lines 1-1 of 1]")
    shutil.rmtree(r)


def test_read_file_range_is_bounded_in_total_across_many_lines():
    """One line no longer explodes, so the second half: many lines still add up."""
    r = _tmp_repo()
    (r / "wide.txt").write_text("\n".join("y" * 500 for _ in range(400)), encoding="utf-8")
    out = Workspace(r).read_file("wide.txt", start=1, end=400)
    assert len(out) <= MAX_READ_CHARS + 200, f"range returned {len(out)} chars"
    assert "[capped]" in out                      # the header says so too, not just the body
    assert "narrow the range with start/end" in out
    # The middle is what goes, so both ends of the selection are still readable.
    assert out.count("y" * 500) >= 2
    shutil.rmtree(r)


def test_read_file_range_elision_never_hides_that_it_happened():
    """An elision a model cannot see is how it reports reading what it did not."""
    r = _tmp_repo()
    (r / "blob.json").write_text("z" * 100_000 + "\n" + "w" * 100_000, encoding="utf-8")
    out = Workspace(r).read_file("blob.json", start=1, end=2)
    assert "elided" in out
    for marker in ("[line 1 elided", "[line 2 elided"):
        assert marker in out, marker
    assert len(out) < 10_000
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


# --- role-gated capability (Part B1) -----------------------------------------
# A read-only role must never be OFFERED write_file. The role prompts already say
# "read-only" in prose and this node overrides prose (0/8), so the fix is
# capability: do not hand it the tool.

def test_read_only_role_is_not_offered_write_file():
    r = _tmp_repo()
    ws = Workspace(r, {"tools": ["workspace"], "write": False})
    names = {s["function"]["name"] for s in ws.tool_schemas()}
    assert "write_file" not in names
    assert {"list_tree", "read_file", "glob"} <= names
    shutil.rmtree(r)


def test_write_capable_roles_are_offered_write_file():
    """Absent `write` keeps historical behaviour; so does an explicit true."""
    r = _tmp_repo()
    for spec in ({}, {"tools": ["workspace"]}, {"tools": ["workspace"], "write": True}):
        names = {s["function"]["name"] for s in Workspace(r, spec).tool_schemas()}
        assert "write_file" in names, spec
    shutil.rmtree(r)


def test_no_spec_leaves_write_untouched():
    """A direct Workspace(root) call is not a registry run; do not change it."""
    r = _tmp_repo()
    ws = Workspace(r)
    assert ws.allows_write() is True
    assert ws.write_file("apps/ok.ts", "x").startswith("wrote")
    shutil.rmtree(r)


def test_read_only_role_write_file_call_is_refused_anyway():
    """Defence in depth: a model can emit a call for a tool it was NOT offered.

    Being absent from the schema is not itself an enforcement, so write_file
    refuses on the role as well.
    """
    r = _tmp_repo()
    ws = Workspace(r, {"tools": ["workspace"], "write": False})
    out = ws.write_file("apps/ok.ts", "x")
    assert out.startswith("ERROR: refusing to write")
    assert "read-only" in out
    assert not (r / "apps" / "ok.ts").exists()
    # ...and the read tools still work for that role
    assert "export const x" in ws.read_file("apps/a.test.ts")
    shutil.rmtree(r)


def test_role_without_the_workspace_group_gets_no_workspace_tools():
    r = _tmp_repo()
    assert Workspace(r, {"tools": ["exec"]}).tool_schemas() == []
    shutil.rmtree(r)


def test_empty_tools_defaults_to_the_workspace_group():
    """`tools: []` is how pre-existing registries spell it; must stay permissive."""
    r = _tmp_repo()
    names = {s["function"]["name"] for s in Workspace(r, {"tools": []}).tool_schemas()}
    assert names == {"list_tree", "read_file", "glob", "write_file"}
    shutil.rmtree(r)


def test_per_role_write_deny_blocks_that_prefix_only():
    r = _tmp_repo()
    ws = Workspace(r, {"write_deny": ["emails"]})
    assert ws.write_file("emails/draft.md", "x").startswith("ERROR: refusing")
    assert ws.write_file("emails", "x").startswith("ERROR: refusing")
    assert ws.write_file("emails2/x.md", "x").startswith("wrote")   # not a prefix of this
    shutil.rmtree(r)


def test_per_role_write_scope_confines_writes():
    r = _tmp_repo()
    ws = Workspace(r, {"write_scope": ["repos/pvl-rentals"]})
    assert ws.write_file("repos/pvl-rentals/src/a.ts", "x").startswith("wrote")
    out = ws.write_file("records/notes.md", "x")
    assert out.startswith("ERROR: refusing")
    assert "write scope" in out
    shutil.rmtree(r)


def test_write_deny_accepts_a_bare_string():
    r = _tmp_repo()
    ws = Workspace(r, {"write_deny": "emails"})
    assert ws.write_file("emails/x.md", "x").startswith("ERROR: refusing")
    shutil.rmtree(r)


def test_per_role_deny_cannot_override_the_unconditional_list():
    """A role's own policy is additive; it can never re-open `.solar/`."""
    r = _tmp_repo()
    ws = Workspace(r, {"write": True, "write_scope": [".solar"]})
    assert ws.write_file(".solar/registry.json", "x").startswith("ERROR: refusing")
    shutil.rmtree(r)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"all {len(fns)} workspace tests passed")
