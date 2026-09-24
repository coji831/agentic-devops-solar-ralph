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

from solar_governor.workspace import MAX_READ_CHARS, SEARCH_MAX_CHARS, Workspace  # noqa: E402


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
    assert names == {"list_tree", "read_file", "glob", "search_text", "write_file",
                     "replace_in_file"}
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
    """`None` at the layer, the message at the composite.

    The old shape raised `ERROR: unknown tool` inside every layer, one method above a predicate
    that answered the same question; now the layer returns `None` and the composite - the only
    caller that knows the other layers exist - says it once.
    """
    from solar_governor.executor import _ToolLayer

    r = _tmp_repo()
    assert Workspace(r).call_tool("nope", {}) is None
    assert _ToolLayer(Workspace(r)).call_tool("nope", {}) == "ERROR: unknown tool nope"
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
    # Asserted as a SET and from the single source, so a THIRD mutator cannot arrive unconsidered:
    # a hand-written list here would have said nothing about `replace_in_file` (2026-09-21).
    assert not (set(ws._MUTATING_TOOLS) & names), f"a read-only role was offered {sorted(names)}"
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
    assert names == {"list_tree", "read_file", "glob", "search_text", "write_file",
                     "replace_in_file"}
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


def test_a_default_install_reviewer_is_not_offered_write_file():
    """The SHIPPED default registry, not a hand-written spec - which is the whole point of the test.

    Found 2026-09-20 by the wiretap of T1.1. `DEFAULT_SPECIALISTS["reviewer"]` omitted `write`, and
    `allows_write()` reads an omitted key as YES - so a fresh install handed `write_file` to the one
    built-in role whose product is a verdict rather than an edit, **which let a reviewer edit the
    output it was reviewing.** `tool_schemas`'s own docstring promised the opposite, so the defect
    was never a wrong rule; it was a rule the registry did not carry.

    **Measured before the fix**, at a default install: the tool list was
    `['list_tree', 'read_file', 'glob', 'write_file']` and `records/x.md`, `docs/x.md` and
    `emails/x.md` all wrote. `../repos/PTM-EC/x.ts` and `package.json` did not, so the unconditional
    deny list was holding - the gap was everything else.
    """
    from solar_governor.registry import DEFAULT_SPECIALISTS
    r = _tmp_repo()
    ws = Workspace(r, DEFAULT_SPECIALISTS["reviewer"])
    names = {s["function"]["name"] for s in ws.tool_schemas()}
    assert "write_file" not in names, f"a reviewer was handed write_file: {sorted(names)}"
    assert not (set(ws._MUTATING_TOOLS) & names), f"a reviewer was handed {sorted(names)}"
    # Offered is not the enforcement, so the CALL is asserted too: a model can emit a call for a
    # tool it was never given, and "not offered" is not by itself a refusal.
    assert ws.write_file("records/x.md", "x").startswith("ERROR: refusing")
    shutil.rmtree(r)


def test_a_default_install_implementer_may_still_write():
    """The other half, so the fix above cannot be mistaken for 'deny everything'."""
    from solar_governor.registry import DEFAULT_SPECIALISTS
    r = _tmp_repo()
    ws = Workspace(r, DEFAULT_SPECIALISTS["implementer"])
    names = {s["function"]["name"] for s in ws.tool_schemas()}
    assert "write_file" in names, f"an implementer lost its write tool: {sorted(names)}"
    assert ws.write_file("apps/x.ts", "x").startswith("wrote")
    shutil.rmtree(r)


def test_every_built_in_role_states_its_write_capability():
    """**The default must not be reachable by OMISSION.** `allows_write()` reads a missing `write`
    key as True, so a built-in that forgets it is a built-in that may write - and the absence is
    invisible in a diff. This asserts the key is PRESENT on every shipped role, which is what stops
    the same defect from arriving again under a different role name."""
    from solar_governor.registry import DEFAULT_SPECIALISTS
    silent = sorted(name for name, spec in DEFAULT_SPECIALISTS.items() if "write" not in spec)
    assert not silent, (f"{silent} omit `write`, and an omitted key means ALLOW - declare it, "
                        f"whichever way it goes")


# --- replace_in_file: the bounded edit (2026-09-21) --------------------------
# Added because `write_file` was this layer's ONLY mutator and it OVERWRITES. A 101 KB message
# catalog could therefore only be changed by reconstructing it out of reads capped at
# MAX_READ_CHARS and writing the whole thing back - which, measured on 2026-09-21 in the Promyro
# engagement, returned 820 lines and DELETED 2690 of a 2746-line file. These tests pin the property
# that makes that impossible rather than merely discouraged: an anchor that is not exactly unique
# changes NOTHING.

def test_replace_in_file_edits_one_anchor_and_leaves_the_rest_byte_identical():
    r = _tmp_repo()
    p = r / "apps" / "a.test.ts"
    before = p.read_text(encoding="utf-8")
    out = Workspace(r).replace_in_file("apps/a.test.ts", "export const x = 1;",
                                       "export const x = 2;")
    assert out.startswith("edited apps/a.test.ts")
    assert p.read_text(encoding="utf-8") == before.replace("export const x = 1;",
                                                          "export const x = 2;")
    shutil.rmtree(r)


def test_replace_in_file_edits_a_file_FAR_larger_than_the_read_cap():
    """THE reason this tool exists. The file cannot be held in one read, and the edit still lands
    with both the beginning and the far end intact - which is the thing write_file could not do."""
    r = _tmp_repo()
    body = "\n".join(f'  "k{i}": "v{i}",' for i in range(6000))
    p = r / "apps" / "huge.json"
    p.write_text('{\n' + body + '\n  "anchor": "old"\n}\n', encoding="utf-8")
    assert p.stat().st_size > MAX_READ_CHARS, "the fixture must exceed the read cap to be a test"
    before_size = p.stat().st_size
    out = Workspace(r).replace_in_file("apps/huge.json", '"anchor": "old"',
                                       '"anchor": "replacement"')
    assert out.startswith("edited")
    # A delta that is not zero, so a silent whole-file rewrite cannot pass by coincidence.
    assert p.stat().st_size == before_size + len("replacement") - len("old")
    text = p.read_text(encoding="utf-8")
    assert '"anchor": "replacement"' in text
    assert '"k5999": "v5999",' in text, "the far end of the file was lost"
    shutil.rmtree(r)


def test_replace_in_file_refuses_a_missing_anchor_without_writing():
    r = _tmp_repo()
    p = r / "apps" / "a.test.ts"
    before = p.read_text(encoding="utf-8")
    out = Workspace(r).replace_in_file("apps/a.test.ts", "NOT IN THE FILE", "x")
    assert out.startswith("ERROR")
    assert "not found" in out
    assert p.read_text(encoding="utf-8") == before
    shutil.rmtree(r)


def test_replace_in_file_refuses_an_ambiguous_anchor_without_writing():
    """Two matches must not silently edit 'the first one', and must not edit both. Mutation test:
    drop the count guard and this fails, which is what makes it a test rather than a decoration."""
    r = _tmp_repo()
    p = r / "apps" / "dup.txt"
    p.write_text("same\nsame\n", encoding="utf-8")
    out = Workspace(r).replace_in_file("apps/dup.txt", "same", "different")
    assert out.startswith("ERROR")
    assert "2 times" in out
    assert p.read_text(encoding="utf-8") == "same\nsame\n"
    shutil.rmtree(r)


def test_replace_in_file_refuses_an_empty_anchor():
    """`str.count("")` is len+1, so an empty anchor would read as ambiguous - say it plainly."""
    r = _tmp_repo()
    out = Workspace(r).replace_in_file("apps/a.test.ts", "", "x")
    assert out.startswith("ERROR")
    assert "empty" in out
    shutil.rmtree(r)


def test_replace_in_file_cannot_create_a_file():
    """It edits; it does not create. If it could create, it could also truncate into existence."""
    r = _tmp_repo()
    out = Workspace(r).replace_in_file("apps/new.ts", "x", "y")
    assert out.startswith("ERROR")
    assert not (r / "apps" / "new.ts").exists()
    shutil.rmtree(r)


def test_replace_in_file_runs_the_same_policy_as_write_file():
    """One policy, two mutators: the escape and the unconditional deny list both hold."""
    r = _tmp_repo()
    ws = Workspace(r)
    assert ws.replace_in_file("../../escape.txt", "a", "b").startswith("ERROR")
    assert ws.replace_in_file(".solar/registry.json", "implementer", "x").startswith("ERROR")
    shutil.rmtree(r)


def test_replace_in_file_preserves_line_endings():
    """A CRLF file comes back CRLF. `write_file` cannot promise this; this one can, because it
    only ever writes back the text it read. A repo kept in LF must not come back in CRLF."""
    r = _tmp_repo()
    p = r / "apps" / "crlf.txt"
    p.write_bytes(b"one\r\ntwo\r\n")
    assert Workspace(r).replace_in_file("apps/crlf.txt", "two", "TWO").startswith("edited")
    assert p.read_bytes() == b"one\r\nTWO\r\n"
    shutil.rmtree(r)


def test_replace_in_file_is_refused_for_a_read_only_role():
    """The CALL is refused as well as the schema withheld - defence in depth, as for write_file."""
    r = _tmp_repo()
    ws = Workspace(r, {"tools": ["workspace"], "write": False})
    assert "replace_in_file" not in {s["function"]["name"] for s in ws.tool_schemas()}
    out = ws.replace_in_file("apps/a.test.ts", "export const x = 1;", "export const x = 9;")
    assert out.startswith("ERROR: refusing to edit")
    assert "read-only" in out
    assert "export const x = 1;" in (r / "apps" / "a.test.ts").read_text(encoding="utf-8")
    shutil.rmtree(r)


def test_a_default_install_reviewer_is_not_offered_replace_in_file():
    """The shipped-default hazard one tool later: `replace_in_file` mutates, so the reviewer must
    be offered neither mutator and refused if it calls one anyway."""
    from solar_governor.registry import DEFAULT_SPECIALISTS
    r = _tmp_repo()
    ws = Workspace(r, DEFAULT_SPECIALISTS["reviewer"])
    names = {s["function"]["name"] for s in ws.tool_schemas()}
    assert not (set(ws._MUTATING_TOOLS) & names), f"a reviewer was handed {sorted(names)}"
    assert ws.replace_in_file("records/x.md", "a", "b").startswith("ERROR: refusing")
    shutil.rmtree(r)


# --- C2: the glob governs READS too (2026-09-20) -----------------------------
# The write half of `write_glob` shipped first and was useless on its own: measured 2026-09-20, the
# agent could not LIST the sibling it could write to, could not read the files it was told to match
# in style, and could not read back what it wrote. It refused to write anything and said so. These
# tests pin both halves and the rule that keeps the grant narrow.

SIBLING_GLOB = {"write": True, "write_glob": ["../repos/sandbox/**"]}


def _root_and_sibling() -> Path:
    """A repo and a SIBLING of it - the shape the grant exists for.

    The clones sit at `Freelance/repos/<name>`, outside the engagement folder the runtime is rooted
    at, so `../repos/sandbox` is not a convenience: it is the only spelling that addresses one. The
    sibling carries the three files a deny list is about - `.git/config` (which can hold a token in
    a remote URL), `.env`, and `package.json` - because a fixture without them cannot prove the
    read denial does anything.
    """
    base = Path(tempfile.mkdtemp(prefix="solar-sib-"))
    root, sib = base / "engagement", base / "repos" / "sandbox"
    (root / "src").mkdir(parents=True)
    (root / "src" / "a.ts").write_text("export const a = 1;\n", encoding="utf-8")
    (root / "package.json").write_text('{"name": "ours"}\n', encoding="utf-8")
    (sib / "src").mkdir(parents=True)
    (sib / "src" / "inventory.js").write_text("exports.stock = 1;\n", encoding="utf-8")
    (sib / ".git").mkdir()
    (sib / ".git" / "config").write_text("[remote]\n\turl = https://tok@github.com/x\n",
                                        encoding="utf-8")
    (sib / ".env").write_text("SECRET=1\n", encoding="utf-8")
    (sib / ".env.local").write_text("SECRET=2\n", encoding="utf-8")
    (sib / "package.json").write_text('{"name": "theirs"}\n', encoding="utf-8")
    return root


def _refusal(fn, *args, **kwargs) -> str:
    """The message a refusal RAISES with, or a marker when the call returned instead.

    The read layer refuses by raising (`resolve_in_root`'s contract) and `call_tool` turns that into
    an `ERROR:` string. **Both surfaces are asserted**, because a test that only checked `call_tool`
    would still pass if the raise were replaced by a quiet empty answer - and an empty answer is the
    failure that reads as a pass.
    """
    try:
        out = fn(*args, **kwargs)
    except ValueError as exc:
        return str(exc)
    return f"<returned instead of raising: {str(out)[:70]}>"


def test_a_glob_covered_sibling_can_be_listed():
    root = _root_and_sibling()
    ws = Workspace(root, SIBLING_GLOB)
    listing = ws.list_tree("../repos/sandbox")
    assert "inventory.js" in listing, listing
    # The listing names only what the READ layer will accept: `.git` and `.env` do not appear, so a
    # model cannot spend a round discovering them.
    assert ".env" not in listing, listing
    assert ".git" not in listing, listing
    shutil.rmtree(root.parent)


def test_a_glob_covered_sibling_can_be_read():
    root = _root_and_sibling()
    ws = Workspace(root, SIBLING_GLOB)
    out = ws.read_file("../repos/sandbox/src/inventory.js")
    assert "exports.stock = 1" in out, out
    # Numbered, because that is how an `http` link earns its `path:line` contract.
    assert "1| " in out, out
    shutil.rmtree(root.parent)


def test_a_sibling_the_glob_does_not_cover_still_raises():
    """**The default answer is unchanged.** One glob admits one tree; everything else escapes."""
    root = _root_and_sibling()
    (root.parent / "repos" / "other" / "src").mkdir(parents=True)
    (root.parent / "repos" / "other" / "src" / "x.ts").write_text("x\n", encoding="utf-8")
    ws = Workspace(root, SIBLING_GLOB)
    assert "escapes repo root" in _refusal(ws.read_file, "../repos/other/src/x.ts")
    assert "escapes repo root" in _refusal(ws.list_tree, "../repos/other")
    shutil.rmtree(root.parent)


def test_the_read_denial_holds_inside_the_grant():
    """`.git`, `.env` and a lockfile are covered by the glob and still unreadable - and the refusal
    names the rule, so a reader can tell WHICH list refused."""
    root = _root_and_sibling()
    ws = Workspace(root, SIBLING_GLOB)
    for rel, expected in (("../repos/sandbox/.git/config", ".git/"),
                          ("../repos/sandbox/.env", "credentials"),
                          ("../repos/sandbox/.env.local", "credentials"),
                          ("../repos/sandbox/package.json", "tooling")):
        assert expected in _refusal(ws.read_file, rel), (rel, _refusal(ws.read_file, rel))
    shutil.rmtree(root.parent)


def test_the_read_denial_does_NOT_apply_inside_the_root():
    """Our own `package.json` stays readable. The deny lists exist because a sibling is somebody
    else's tree - applying them at home would be a restriction nobody asked for."""
    root = _root_and_sibling()
    ws = Workspace(root, SIBLING_GLOB)
    assert "ours" in ws.read_file("package.json")
    shutil.rmtree(root.parent)


def test_a_collapsed_escape_cannot_arrive_at_the_sibling_obliquely():
    """`..` is collapsed BEFORE the glob is matched, so a path that only lands in the sibling after
    three `..`s is judged on where it ends up, not on how it got there."""
    root = _root_and_sibling()
    ws = Workspace(root, SIBLING_GLOB)
    sneaky = "../repos/sandbox/src/../../../repos/sandbox/src/inventory.js"
    assert "exports.stock = 1" in ws.read_file(sneaky), "collapse should still land inside the grant"
    outside = "../repos/sandbox/../../secrets.txt"
    assert "escapes repo root" in _refusal(ws.read_file, outside), _refusal(ws.read_file, outside)
    shutil.rmtree(root.parent)


def test_glob_reaches_a_sibling_only_when_the_pattern_names_it():
    root = _root_and_sibling()
    ws = Workspace(root, SIBLING_GLOB)
    named = ws.glob("../repos/sandbox/src/*.js")
    assert named.strip() == "../repos/sandbox/src/inventory.js", named
    # A bare pattern still means THE ROOT. Widening it silently would make the result set a thing
    # the caller did not ask for.
    bare = ws.glob("**/*.ts")
    assert "a.ts" in bare and "inventory" not in bare, bare
    shutil.rmtree(root.parent)


def test_glob_does_not_match_a_denied_path():
    """Matched-and-refused would cost a round; the denied path is not offered at all."""
    root = _root_and_sibling()
    ws = Workspace(root, SIBLING_GLOB)
    assert "(no matches)" in ws.glob("../repos/sandbox/.env*")
    shutil.rmtree(root.parent)


def test_the_tool_description_names_the_reachable_roots():
    """The grant is unusable if the model cannot find it - measured 2026-09-20, when the agent
    tried all three read tools, was refused, and wrote nothing."""
    root = _root_and_sibling()
    ws = Workspace(root, SIBLING_GLOB)
    described = {s["function"]["name"]: s["function"]["description"] for s in ws.tool_schemas()}
    for tool in ("list_tree", "read_file", "glob"):
        assert "../repos/sandbox/" in described[tool], (tool, described[tool])
    # and no note when the role reaches nowhere, so the description does not nag
    plain = Workspace(root, {"write": True})
    assert "Reachable siblings" not in plain.tool_schemas()[0]["function"]["description"]
    shutil.rmtree(root.parent)


def test_reading_through_a_glob_needs_no_write_permission():
    """The two halves are separate grants for a reason: a read-only role may be sent to a sibling to
    report on it, and `write: False` must not take the read away."""
    root = _root_and_sibling()
    ws = Workspace(root, {"write": False, "write_glob": ["../repos/sandbox/**"]})
    assert "inventory" in ws.read_file("../repos/sandbox/src/inventory.js")
    assert ws.write_file("../repos/sandbox/src/new.js", "x").startswith("ERROR: refusing")
    shutil.rmtree(root.parent)


# --- search_text (T34, 2026-09-23) ------------------------------------------
# The `http` runner's only way to find a fact was to list a tree and read whole files, and
# `messages` is never trimmed - so every read is re-sent and the cost is quadratic in the rounds.
# These cases pin the two halves of the fix: a hit that can be CITED, and a miss that says how
# far it looked.

def test_search_text_finds_a_line_and_spells_it_for_a_citation():
    """`path:line: text` is the point: a hit that cannot be cited costs a round to confirm."""
    r = _tmp_repo()
    out = Workspace(r).search_text("export const")
    assert "apps/a.test.ts:1: export const x = 1;" in out, out
    shutil.rmtree(r)


def test_search_text_skips_vendored_and_binary_and_counts_what_it_READ():
    """The miss has to say how far it looked.

    `(no matches)` alone is indistinguishable from "the tool did not look", and the model pays a
    round to find out which - which is the round this tool exists to remove.
    """
    r = _tmp_repo()
    out = Workspace(r).search_text("module.exports")
    assert "no matches" in out, out
    assert "dep.js" not in out, out              # under node_modules
    assert "1 file(s)" in out, out               # only apps/a.test.ts was ever read
    shutil.rmtree(r)


def test_search_text_accepts_a_single_file_as_the_thing_to_search():
    r = _tmp_repo()
    out = Workspace(r).search_text("export const", rel="apps/a.test.ts")
    assert "a.test.ts:1:" in out and "1 file(s)" in out, out
    shutil.rmtree(r)


def test_search_text_refuses_an_empty_pattern_without_reading_anything():
    """An empty regex matches every line of every file - a whole-tree dump as one call."""
    r = _tmp_repo()
    out = Workspace(r).search_text("")
    assert out.startswith("ERROR: refusing an empty pattern"), out
    shutil.rmtree(r)


def test_search_text_reports_a_bad_regex_instead_of_raising():
    """A refused pattern must come back as a string the model can act on in the same round."""
    r = _tmp_repo()
    out = Workspace(r).search_text("a(")
    assert out.startswith("ERROR: bad regex"), out
    shutil.rmtree(r)


def test_search_text_include_narrows_by_name_or_by_path():
    """One call narrows; three calls is the cost the tool is here to remove."""
    r = _tmp_repo()
    (r / "apps" / "b.py").write_text("export const y = 2;\n", encoding="utf-8")
    ws = Workspace(r)
    assert "b.py" in ws.search_text("export const", include="*.py")
    ts_only = ws.search_text("export const", include="*.ts")
    assert "a.test.ts" in ts_only and "b.py" not in ts_only, ts_only
    shutil.rmtree(r)


def test_search_text_ignore_case_is_opt_in():
    r = _tmp_repo()
    ws = Workspace(r)
    assert "no matches" in ws.search_text("EXPORT CONST")
    assert "a.test.ts" in ws.search_text("EXPORT CONST", ignore_case=True)
    shutil.rmtree(r)


def test_search_text_caps_name_themselves():
    """A capped list that looks complete is how a model concludes it has seen everything."""
    r = _tmp_repo()
    (r / "apps" / "many.txt").write_text("".join(f"needle {i}\n" for i in range(50)),
                                          encoding="utf-8")
    out = Workspace(r).search_text("needle", max_matches=3)
    assert "3 match(es)" in out, out
    assert "stopped at max_matches=3" in out, out
    shutil.rmtree(r)


def test_search_text_says_when_it_only_looked_at_part_of_the_tree():
    """A hit list bounded at file 17 of 187 must not read as the whole answer."""
    r = _tmp_repo()
    for i in range(4):
        (r / "apps" / f"m{i}.txt").write_text(
            "".join(f"needle {i} " + "z" * 200 + "\n" for _ in range(40)), encoding="utf-8")
    out = Workspace(r).search_text("needle")
    assert "the first" in out, out
    assert "char budget" in out, out
    shutil.rmtree(r)


def test_search_text_clips_a_hit_to_a_POINTER_not_a_reading():
    """Measured 2026-09-23: at `read_file`'s 4000-char line budget, two wide table rows spent the
    whole result budget on two hits and cut the walk at 17 of 187 files."""
    r = _tmp_repo()
    (r / "apps" / "wide.txt").write_text("y" * 3_000 + " needle\n", encoding="utf-8")
    out = Workspace(r).search_text("needle")
    assert "[line 1 elided: 3007 chars, first 400 shown]" in out, out
    shutil.rmtree(r)


def test_search_text_holds_its_own_budget_under_the_executor_cap():
    """It caps itself, because the executor's cap cuts the TAIL - which would delete the
    `narrow it` marker first and leave the hit list looking complete."""
    r = _tmp_repo()
    (r / "apps" / "wide.txt").write_text("".join("x" * 300 + "needle\n" for _ in range(40)),
                                          encoding="utf-8")
    out = Workspace(r).search_text("needle")
    assert len(out) <= SEARCH_MAX_CHARS + 400, len(out)
    assert "char budget" in out, out
    shutil.rmtree(r)


def test_a_read_only_role_is_offered_search_text():
    """Search is a READ, and the role that may not write is the one that most needs to find
    something without reading whole files."""
    r = _tmp_repo()
    names = {s["function"]["name"] for s in Workspace(r, {"write": False}).tool_schemas()}
    assert "search_text" in names, names
    assert "write_file" not in names, names
    shutil.rmtree(r)


def test_search_text_reaches_a_glob_named_sibling_and_keeps_the_read_denial():
    """A search that cannot reach the clone cannot find the code the work is about - and
    reaching it must not turn the read deny list into a suggestion."""
    root = _root_and_sibling()
    ws = Workspace(root, SIBLING_GLOB)
    out = ws.search_text("exports.stock", rel="../repos/sandbox")
    assert "../repos/sandbox/src/inventory.js:1: exports.stock = 1;" in out, out
    # `.env`, `.env.local` and their `package.json` are read-denied FOR A SIBLING, so a search
    # must not become the way around the denial.
    assert "no matches" in ws.search_text("SECRET", rel="../repos/sandbox")
    assert "no matches" in ws.search_text("theirs", rel="../repos/sandbox")
    shutil.rmtree(root.parent)


def test_search_text_inside_the_root_denies_nothing():
    """The deny list exists because a sibling is somebody else's tree. Applying it inside our
    own would be a restriction nobody asked for - and `package.json` is in it."""
    root = _root_and_sibling()
    ws = Workspace(root, SIBLING_GLOB)
    assert "ours" in ws.search_text("ours", rel=".")
    shutil.rmtree(root.parent)


def test_search_text_on_an_ungranted_sibling_is_an_error_string_not_a_crash():
    root = _root_and_sibling()
    ws = Workspace(root, {"write": False})
    out = ws.call_tool("search_text", {"pattern": "stock", "rel": "../repos/sandbox"})
    assert out.startswith("ERROR:"), out
    shutil.rmtree(root.parent)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"all {len(fns)} workspace tests passed")
