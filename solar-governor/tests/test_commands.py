"""Tests for the vetted command vocabulary (patch Part C) and the approval gate (Part D).

Two properties matter more than the features here:

1. A command that is not declared, or not GRANTED to the role, must not exist for that
   role. Absence is the containment - a rule asking the model to avoid a command is not.
2. There is no free-text command or argument field, so a vocabulary command cannot be
   turned into an arbitrary one. **The one argument that exists is a PATH, declared by
   the command (`accepts`), resolved against that command's own `cwd`, and refused
   unless it names a real file there** - see the `accepts` section at the bottom.

Everything runs offline against the local interpreter as argv[0], so the suite needs no
network and no project toolchain. No API key is required.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solar_governor.commands import (  # noqa: E402
    CLONE, CLONE_NONE, CommandRunner, clone_problem, clone_required, load_vocabulary)

PY = sys.executable


def _tmp_repo(vocabulary: dict | None = None, spec: dict | None = None,
              human_approval: bool = False, clone: str = "") -> tuple[Path, CommandRunner]:
    r = Path(tempfile.mkdtemp(prefix="solar-cmd-"))
    (r / ".solar").mkdir(parents=True)
    (r / "sub").mkdir()
    if vocabulary is not None:
        (r / ".solar" / "commands.json").write_text(json.dumps(vocabulary),
                                                    encoding="utf-8")
    return r, CommandRunner(r, spec, human_approval=human_approval, clone=clone)


def _vocab(**commands) -> dict:
    """A vocabulary whose entries all invoke the local interpreter."""
    return {name: {"argv": [PY, "-c", code], "kind": kind, "timeout": 30}
            for name, (code, kind) in commands.items()}


# --- what the model is offered ----------------------------------------------

def test_no_vocabulary_file_means_no_command_tool():
    r, cr = _tmp_repo(spec={"tools": ["workspace", "exec"], "exec_allow": ["anything"]})
    assert cr.tool_schemas() == []
    shutil.rmtree(r)


def test_no_exec_allow_means_no_command_tool_even_with_a_vocabulary():
    """exec is opt-in and defaults to nothing - the opposite of `write`, which had to
    default to allowed for backward compatibility. No existing registry could have
    relied on exec, so the safe default is available here."""
    r, cr = _tmp_repo(vocabulary=_vocab(hello=("print('hi')", "read")),
                      spec={"tools": ["workspace", "exec"]})
    assert cr.tool_schemas() == []
    assert cr.granted() == {}
    shutil.rmtree(r)


def test_only_granted_commands_appear_in_the_enum():
    r, cr = _tmp_repo(vocabulary=_vocab(a=("print('a')", "read"), b=("print('b')", "read")),
                      spec={"exec_allow": ["a"]})
    schemas = cr.tool_schemas()
    assert len(schemas) == 1
    params = schemas[0]["function"]["parameters"]
    assert params["properties"]["command"]["enum"] == ["a"]
    assert params["required"] == ["command"]
    shutil.rmtree(r)


def test_the_tool_offers_no_free_text_field():
    """The only param is the command NAME. No argv, no args, no shell string."""
    r, cr = _tmp_repo(vocabulary=_vocab(a=("print('a')", "read")),
                      spec={"exec_allow": ["a"]})
    params = cr.tool_schemas()[0]["function"]["parameters"]["properties"]
    assert list(params) == ["command"]
    assert "enum" in params["command"]
    shutil.rmtree(r)


def test_handles_only_the_command_tool():
    r, cr = _tmp_repo(spec={"exec_allow": []})
    assert cr.handles("run_command") is True
    assert cr.handles("read_file") is False
    assert cr.handles("write_file") is False
    shutil.rmtree(r)


# --- execution --------------------------------------------------------------

def test_granted_command_runs_and_is_shaped():
    r, cr = _tmp_repo(vocabulary=_vocab(hello=("print('hello world')", "check")),
                      spec={"exec_allow": ["hello"]})
    out = cr.call_tool("run_command", {"command": "hello"})
    assert "[hello] PASS exit 0" in out
    assert "kind=check" in out
    assert "result: PASSED" in out          # a passing check carries no body (Part E)
    shutil.rmtree(r)


def test_a_failing_command_is_reported_not_raised():
    """A checker that fails is the SIGNAL, not an exception - the node has to read it."""
    r, cr = _tmp_repo(vocabulary=_vocab(
        boom=("print('the reason it failed'); import sys; sys.exit(3)", "check")),
        spec={"exec_allow": ["boom"]})
    out = cr.call_tool("run_command", {"command": "boom"})
    assert "[boom] FAIL exit 3" in out
    assert "the reason it failed" in out     # the final line is always kept
    shutil.rmtree(r)


def test_stderr_is_surfaced():
    r, cr = _tmp_repo(vocabulary=_vocab(noisy=("import sys; print('bad', file=sys.stderr)", "read")),
                      spec={"exec_allow": ["noisy"]})
    out = cr.call_tool("run_command", {"command": "noisy"})
    assert "--- stderr ---" in out and "bad" in out
    shutil.rmtree(r)


def test_timeout_is_enforced():
    r, cr = _tmp_repo(vocabulary={"slow": {"argv": [PY, "-c", "import time; time.sleep(5)"],
                                           "kind": "check", "timeout": 1}},
                      spec={"exec_allow": ["slow"]})
    out = cr.call_tool("run_command", {"command": "slow"})
    assert "TIMEOUT after 1s" in out
    shutil.rmtree(r)


def test_missing_executable_reports_not_installed():
    """`docker` and `psql` are genuinely absent on the dev box; the tool must degrade
    to a clear message rather than raising."""
    r, cr = _tmp_repo(vocabulary={"ghost": {"argv": ["definitely-not-a-real-exe-xyz"],
                                            "kind": "read", "timeout": 5}},
                      spec={"exec_allow": ["ghost"]})
    out = cr.call_tool("run_command", {"command": "ghost"})
    assert "not installed" in out
    shutil.rmtree(r)


def test_argv0_on_path_is_resolved_through_which():
    """The Windows `.CMD` case: `shell=False` cannot execute `npm` bare, so argv[0]
    must be resolved through shutil.which. Skipped where npm is absent."""
    if shutil.which("npm") is None:
        return
    r, cr = _tmp_repo(vocabulary={"npm_version": {"argv": ["npm", "--version"],
                                                  "kind": "read", "timeout": 60}},
                      spec={"exec_allow": ["npm_version"]})
    out = cr.call_tool("run_command", {"command": "npm_version"})
    assert "exit 0" in out, out
    shutil.rmtree(r)


def test_cwd_is_honoured_and_confined():
    r, cr = _tmp_repo(vocabulary={
        "here": {"argv": [PY, "-c", "import os; print(os.path.basename(os.getcwd()))"],
                 "kind": "read", "timeout": 30},
        "in_sub": {"argv": [PY, "-c", "import os; print(os.path.basename(os.getcwd()))"],
                   "kind": "read", "timeout": 30, "cwd": "sub"},
        "escape": {"argv": [PY, "-c", "print(1)"], "kind": "read", "cwd": "../.."},
    }, spec={"exec_allow": ["here", "in_sub", "escape"]})

    assert r.name in cr.call_tool("run_command", {"command": "here"})
    assert "sub" in cr.call_tool("run_command", {"command": "in_sub"})
    assert cr.call_tool("run_command", {"command": "escape"}).startswith("ERROR")
    shutil.rmtree(r)


def test_invalid_kind_is_rejected():
    r, cr = _tmp_repo(vocabulary={"weird": {"argv": [PY, "-c", "print(1)"], "kind": "sneaky"}},
                      spec={"exec_allow": ["weird"]})
    assert "invalid kind" in cr.call_tool("run_command", {"command": "weird"})
    shutil.rmtree(r)


def test_large_output_is_clipped_keeping_head_and_tail():
    r, cr = _tmp_repo(vocabulary={"big": {"argv": [PY, "-c", "print('A'*300 + 'MID' + 'Z'*300)"],
                                          "kind": "read", "max_output": 200}},
                      spec={"exec_allow": ["big"]})
    out = cr.call_tool("run_command", {"command": "big"})
    assert "chars elided" in out
    assert "AAAA" in out and "ZZZZ" in out
    shutil.rmtree(r)


# --- absence is the mechanism ----------------------------------------------

def test_undeclared_command_is_refused_with_the_reason():
    r, cr = _tmp_repo(vocabulary=_vocab(a=("print(1)", "read")), spec={"exec_allow": ["a"]})
    out = cr.call_tool("run_command", {"command": "npm_run_format"})
    assert out.startswith("ERROR")
    assert "not declared" in out
    shutil.rmtree(r)


def test_declared_but_not_granted_says_so_distinctly():
    """The distinction is the point: `not granted` is a fixable config problem, while
    `not declared` means the command does not exist in this repo at all."""
    r, cr = _tmp_repo(vocabulary=_vocab(a=("print(1)", "read"), b=("print(2)", "read")),
                      spec={"exec_allow": ["a"]})
    out = cr.call_tool("run_command", {"command": "b"})
    assert "not granted to this role" in out
    shutil.rmtree(r)


def test_malformed_vocabulary_entries_are_dropped_not_fatal():
    r = Path(tempfile.mkdtemp(prefix="solar-cmd-"))
    (r / ".solar").mkdir(parents=True)
    (r / ".solar" / "commands.json").write_text(json.dumps({
        "good": {"argv": [PY, "-c", "print(1)"], "kind": "read"},
        "no_argv": {"kind": "read"},
        "argv_not_a_list": {"argv": "npm test"},
        "not_a_dict": "nonsense",
    }), encoding="utf-8")
    vocab = load_vocabulary(r)
    assert list(vocab) == ["good"]
    shutil.rmtree(r)


def test_extra_arguments_are_rejected():
    """There is no argv passthrough to abuse."""
    r, cr = _tmp_repo(vocabulary=_vocab(a=("print(1)", "read")), spec={"exec_allow": ["a"]})
    out = cr.call_tool("run_command", {"command": "a", "args": ["--danger"]})
    assert out.startswith("ERROR")
    shutil.rmtree(r)


def test_unknown_tool_name_is_rejected():
    r, cr = _tmp_repo(spec={"exec_allow": []})
    assert cr.call_tool("not_a_tool", {}).startswith("ERROR: unknown tool")
    shutil.rmtree(r)


def test_env_additions_reach_the_child_only():
    r, cr = _tmp_repo(vocabulary={
        "show": {"argv": [PY, "-c", "import os; print(os.environ.get('SOLAR_TEST_MARKER'))"],
                 "kind": "read", "env": {"SOLAR_TEST_MARKER": "child-only"}},
    }, spec={"exec_allow": ["show"]})
    out = cr.call_tool("run_command", {"command": "show"})
    assert "child-only" in out
    assert "SOLAR_TEST_MARKER" not in os.environ
    shutil.rmtree(r)


# --- Part D: the approval gate ---------------------------------------------

def _act_repo(human_approval: bool, marker: Path):
    """An acting command that leaves a marker if it ever actually runs."""
    code = f"open(r'{marker}', 'w').write('ran')"
    return _tmp_repo(vocabulary={"do_it": {"argv": [PY, "-c", code], "kind": "act",
                                           "timeout": 30,
                                           "describe": "Writes a marker file."}},
                     spec={"exec_allow": ["do_it"]},
                     human_approval=human_approval)


def test_act_command_runs_when_approval_is_off():
    d = Path(tempfile.mkdtemp(prefix="solar-mark-"))
    marker = d / "ran.txt"
    r, cr = _act_repo(False, marker)
    out = cr.call_tool("run_command", {"command": "do_it"})
    assert "exit 0" in out and marker.exists()
    shutil.rmtree(r)
    shutil.rmtree(d)


def test_act_command_does_not_run_without_a_decision():
    """The gate must make the command UNABLE to proceed, not merely unwise."""
    d = Path(tempfile.mkdtemp(prefix="solar-mark-"))
    marker = d / "ran.txt"
    r, cr = _act_repo(True, marker)
    out = cr.call_tool("run_command", {"command": "do_it"})
    assert out.startswith("AWAITING APPROVAL")
    assert not marker.exists(), "an acting command ran without approval"
    proposals = list((r / ".solar" / "approvals").glob("*.md"))
    assert len(proposals) == 1
    body = proposals[0].read_text(encoding="utf-8")
    assert "Writes a marker file." in body          # from config, not the model
    assert "do_it" in body
    shutil.rmtree(r)
    shutil.rmtree(d)


def test_allow_decision_lets_it_run():
    d = Path(tempfile.mkdtemp(prefix="solar-mark-"))
    marker = d / "ran.txt"
    r, cr = _act_repo(True, marker)
    cr.call_tool("run_command", {"command": "do_it"})           # creates the proposal
    aid = next((r / ".solar" / "approvals").glob("*.md")).stem
    (r / ".solar" / "approvals" / f"{aid}.decision").write_text("allow\n", encoding="utf-8")
    out = cr.call_tool("run_command", {"command": "do_it"})
    assert "exit 0" in out and marker.exists()
    shutil.rmtree(r)
    shutil.rmtree(d)


def test_deny_decision_blocks_and_carries_the_reason():
    d = Path(tempfile.mkdtemp(prefix="solar-mark-"))
    marker = d / "ran.txt"
    r, cr = _act_repo(True, marker)
    cr.call_tool("run_command", {"command": "do_it"})
    aid = next((r / ".solar" / "approvals").glob("*.md")).stem
    (r / ".solar" / "approvals" / f"{aid}.decision").write_text(
        "deny: not on a Friday\n", encoding="utf-8")
    out = cr.call_tool("run_command", {"command": "do_it"})
    assert out.startswith("DENIED: not on a Friday")
    assert not marker.exists()
    shutil.rmtree(r)
    shutil.rmtree(d)


def test_the_approval_id_is_stable_across_attempts():
    """A human's decision must still be found on the next attempt, not re-asked."""
    d = Path(tempfile.mkdtemp(prefix="solar-mark-"))
    r, cr = _act_repo(True, d / "ran.txt")
    first = cr.call_tool("run_command", {"command": "do_it"}).split()[2]
    second = cr.call_tool("run_command", {"command": "do_it"}).split()[2]
    assert first == second
    assert len(list((r / ".solar" / "approvals").glob("*.md"))) == 1
    shutil.rmtree(r)
    shutil.rmtree(d)


def test_read_and_check_commands_are_not_gated():
    r, cr = _tmp_repo(vocabulary=_vocab(peek=("print('ok')", "read")),
                      spec={"exec_allow": ["peek"]}, human_approval=True)
    assert "exit 0" in cr.call_tool("run_command", {"command": "peek"})
    shutil.rmtree(r)


# --- the executor's composite surface --------------------------------------

def test_executor_offers_both_layers_gated_by_the_role():
    from solar_governor.executor import _ToolLayer
    from solar_governor.workspace import Workspace

    r, _ = _tmp_repo(vocabulary=_vocab(peek=("print('ok')", "read")))
    spec = {"tools": ["workspace", "exec"], "write": False, "exec_allow": ["peek"]}
    layer = _ToolLayer(Workspace(r, spec), CommandRunner(r, spec))
    names = {s["function"]["name"] for s in layer.tool_schemas()}
    assert names == {"list_tree", "read_file", "glob", "search_text", "run_command"}
    assert "[peek] PASS exit 0" in layer.call_tool("run_command", {"command": "peek"})
    assert layer.call_tool("nope", {}).startswith("ERROR: unknown tool")
    shutil.rmtree(r)


# --- Part E: shaped checker output -----------------------------------------
# Measured on a real Next.js monorepo: a PASSING `npm --silent run typecheck` emits
# 0 chars, and a FAILING `prettier --check .` emits ~31k chars whose only actionable
# line is the last one. An unshaped failure report also cost +10% prompt tokens with
# more rounds (16 §11.3).

def test_passing_check_collapses_to_one_line():
    r, cr = _tmp_repo(vocabulary=_vocab(ok=("print('a'*5000)", "check")),
                      spec={"exec_allow": ["ok"]})
    out = cr.call_tool("run_command", {"command": "ok"})
    assert "] PASS exit 0" in out
    assert "result: PASSED" in out
    assert "aaaa" not in out          # the body is dropped, not carried
    assert len(out) < 200
    shutil.rmtree(r)


def test_failing_check_keeps_failures_and_reports_what_it_hid():
    code = ("print('noise line 1')\n"
            "print('noise line 2')\n"
            "print('src/app.ts:12:5 error Something broke')\n"
            "print('noise line 3')\n"
            "print('4 problems (1 error, 3 hidden)')\n"
            "import sys; sys.exit(1)")
    r, cr = _tmp_repo(vocabulary={"bad": {"argv": [PY, "-c", code], "kind": "check"}},
                      spec={"exec_allow": ["bad"]})
    out = cr.call_tool("run_command", {"command": "bad"})
    assert "[bad] FAIL exit 1" in out
    assert "--- failures" in out
    assert "src/app.ts:12:5 error Something broke" in out
    assert "noise line 1" not in out
    assert "further line(s) suppressed" in out
    # the final line is always kept: it is usually the summary
    assert "4 problems" in out
    shutil.rmtree(r)


def test_summary_only_keeps_just_the_last_line():
    """`prettier --check .` lists 580 files; only the count matters."""
    code = ("print('unrelated chatter')\n"
            "print('Code style issues found in 30 files.')\n"
            "import sys; sys.exit(1)")
    r, cr = _tmp_repo(vocabulary={
        "fmt": {"argv": [PY, "-c", code], "kind": "check",
                "shape": {"summary_only": True}}},
        spec={"exec_allow": ["fmt"]})
    out = cr.call_tool("run_command", {"command": "fmt"})
    assert "Code style issues found in 30 files." in out
    assert "unrelated chatter" not in out
    assert "1 further line(s) suppressed" in out
    shutil.rmtree(r)


def test_declared_keep_regex_overrides_the_default():
    code = ("print('SOMETHING_CUSTOM_42')\nprint('unrelated chatter')\n"
            "print('tail line')\nimport sys; sys.exit(1)")
    r, cr = _tmp_repo(vocabulary={
        "k": {"argv": [PY, "-c", code], "kind": "check",
              "shape": {"keep": "SOMETHING_CUSTOM_\\d+"}}},
        spec={"exec_allow": ["k"]})
    out = cr.call_tool("run_command", {"command": "k"})
    assert "SOMETHING_CUSTOM_42" in out
    assert "unrelated chatter" not in out
    shutil.rmtree(r)


def test_max_items_caps_the_failure_list():
    code = "\n".join([f"print('error number {i}')" for i in range(40)]
                     + ["import sys; sys.exit(1)"])
    r, cr = _tmp_repo(vocabulary={
        "m": {"argv": [PY, "-c", code], "kind": "check",
              "shape": {"max_items": 3}}},
        spec={"exec_allow": ["m"]})
    out = cr.call_tool("run_command", {"command": "m"})
    assert "error number 0" in out and "error number 2" in out
    assert "error number 5" not in out
    # 3 matched by max_items, plus the final line which is always kept = 4 of 40
    assert "error number 39" in out
    assert "36 further line(s) suppressed" in out
    shutil.rmtree(r)


def test_ansi_escapes_are_stripped():
    code = "print('\\x1b[33mwarn\\x1b[39m something \\x1b[1m bold\\x1b[0m')"
    r, cr = _tmp_repo(vocabulary=_vocab(rainbow=(code, "read")),
                      spec={"exec_allow": ["rainbow"]})
    out = cr.call_tool("run_command", {"command": "rainbow"})
    assert "\x1b" not in out
    assert "warn something" in out and "bold" in out
    shutil.rmtree(r)


def test_read_output_is_never_summarised():
    """A READ command's output IS the information - shaping it would destroy it."""
    code = "for i in range(20): print('line', i)"
    r, cr = _tmp_repo(vocabulary=_vocab(peek=(code, "read")),
                      spec={"exec_allow": ["peek"]})
    out = cr.call_tool("run_command", {"command": "peek"})
    assert "line 0" in out and "line 19" in out and "--- stdout ---" in out
    assert "suppressed" not in out
    shutil.rmtree(r)


def test_passing_check_with_no_output_is_not_an_error():
    """`npm --silent run typecheck` on success emits literally nothing."""
    r, cr = _tmp_repo(vocabulary=_vocab(quiet=("pass", "check")),
                      spec={"exec_allow": ["quiet"]})
    out = cr.call_tool("run_command", {"command": "quiet"})
    assert "] PASS exit 0" in out and "result: PASSED" in out
    shutil.rmtree(r)


def test_failing_check_with_no_output_says_so():
    r, cr = _tmp_repo(vocabulary=_vocab(mute=("import sys; sys.exit(2)", "check")),
                      spec={"exec_allow": ["mute"]})
    out = cr.call_tool("run_command", {"command": "mute"})
    assert "] FAIL exit 2" in out
    assert "produced no output" in out
    shutil.rmtree(r)


def test_nonzero_exit_is_normalised_from_the_windows_dword():
    """Windows surfaces a failing exit as e.g. 4294967294, which teaches nothing."""
    r, cr = _tmp_repo(vocabulary=_vocab(neg=("import sys; sys.exit(-2)", "check")),
                      spec={"exec_allow": ["neg"]})
    out = cr.call_tool("run_command", {"command": "neg"})
    assert "exit -2" in out
    assert "4294967" not in out
    shutil.rmtree(r)


def test_a_long_failure_line_is_clipped():
    code = "print('error ' + 'x'*3000); import sys; sys.exit(1)"
    r, cr = _tmp_repo(vocabulary={"long": {"argv": [PY, "-c", code], "kind": "check"}},
                      spec={"exec_allow": ["long"]})
    out = cr.call_tool("run_command", {"command": "long"})
    assert "chars elided" in out
    shutil.rmtree(r)


# --- one path, and only where the command declares it (T40) ------------------
#
# The property under test is NOT "a path can be passed". It is that a path is the ONLY thing that
# can be added to a frozen argv, that it is validated against the command's own cwd rather than
# substituted into the declaration, and that a command which takes no argument refuses one instead
# of quietly running something other than what was asked for.

def _path_vocab(**commands) -> dict:
    """Entries that echo their own arguments, so what arrived is what is asserted."""
    return {name: {"argv": [PY, "-c", "import sys; print('ARGV:', sys.argv[1:])"],
                   "kind": kind, "timeout": 30, **extra}
            for name, (kind, extra) in commands.items()}


def test_a_declared_path_is_appended_to_the_frozen_argv():
    r, cr = _tmp_repo(vocabulary=_path_vocab(one=("read", {"accepts": "path"})),
                      spec={"exec_allow": ["one"]})
    (r / "notes.md").write_text("# notes\n", encoding="utf-8")
    out = cr.call_tool("run_command", {"command": "one", "path": "notes.md"})
    assert "ARGV: ['notes.md']" in out
    assert "path=notes.md" in out  # the target is on the record, like cwd
    shutil.rmtree(r)


def test_the_path_is_resolved_against_the_commands_own_cwd():
    """`cwd`-relative, not root-relative: the child resolves its arguments in its own
    working directory, which is also the base check 47 reads a declared argv from."""
    r, cr = _tmp_repo(vocabulary=_path_vocab(one=("read", {"accepts": "path",
                                                          "cwd": "sub"})),
                      spec={"exec_allow": ["one"]})
    (r / "sub" / "notes.md").write_text("# notes\n", encoding="utf-8")
    assert "ARGV: ['notes.md']" in cr.call_tool("run_command", {"command": "one",
                                                                "path": "notes.md"})
    # the same file named from the ROOT resolves to <cwd>/sub/notes.md, which is not there
    escaped = cr.call_tool("run_command", {"command": "one", "path": "sub/notes.md"})
    assert escaped.startswith("ERROR:")
    shutil.rmtree(r)


def test_a_path_that_escapes_the_root_is_refused():
    r, cr = _tmp_repo(vocabulary=_path_vocab(one=("read", {"accepts": "path"})),
                      spec={"exec_allow": ["one"]})
    out = cr.call_tool("run_command", {"command": "one", "path": "../outside.md"})
    assert out.startswith("ERROR:") and "escapes" in out
    assert "ARGV" not in out  # it never ran
    shutil.rmtree(r)


def test_a_path_that_is_not_a_file_is_refused():
    r, cr = _tmp_repo(vocabulary=_path_vocab(one=("read", {"accepts": "path"})),
                      spec={"exec_allow": ["one"]})
    assert cr.call_tool("run_command", {"command": "one", "path": "sub"}).startswith("ERROR:")
    assert cr.call_tool("run_command", {"command": "one",
                                         "path": "nothing.md"}).startswith("ERROR:")
    shutil.rmtree(r)


def test_an_argument_cannot_be_composed_into_one():
    """No splitting and no quoting: `--write .` is ONE path, and a path that names no file
    is refused - so a caller cannot turn the vocabulary back into a shell."""
    r, cr = _tmp_repo(vocabulary=_path_vocab(one=("read", {"accepts": "path"})),
                      spec={"exec_allow": ["one"]})
    for attempt in ("--write .", "--write", "notes.md --write"):
        assert cr.call_tool("run_command", {"command": "one",
                                             "path": attempt}).startswith("ERROR:")
    shutil.rmtree(r)


def test_a_command_that_takes_no_path_refuses_one():
    """Silently dropping it would run something other than what was asked for."""
    r, cr = _tmp_repo(vocabulary=_path_vocab(plain=("read", {})),
                      spec={"exec_allow": ["plain"]})
    (r / "notes.md").write_text("# notes\n", encoding="utf-8")
    out = cr.call_tool("run_command", {"command": "plain", "path": "notes.md"})
    assert out.startswith("ERROR:") and "declares no `accepts`" in out
    assert "ARGV" not in out
    shutil.rmtree(r)


def test_a_command_that_declares_accepts_requires_the_path():
    r, cr = _tmp_repo(vocabulary=_path_vocab(one=("read", {"accepts": "path"})),
                      spec={"exec_allow": ["one"]})
    out = cr.call_tool("run_command", {"command": "one"})
    assert out.startswith("ERROR:") and "none was supplied" in out
    shutil.rmtree(r)


def test_the_path_field_is_advertised_only_by_the_commands_that_take_one():
    r, cr = _tmp_repo(vocabulary=_path_vocab(one=("read", {"accepts": "path"}),
                                            plain=("read", {})),
                      spec={"exec_allow": ["one", "plain"]})
    params = cr.tool_schemas()[0]["function"]["parameters"]
    assert sorted(params["properties"]) == ["command", "path"]
    assert params["required"] == ["command"]           # the argument stays optional overall
    assert "one" in params["properties"]["path"]["description"]
    assert "plain" not in params["properties"]["path"]["description"]
    shutil.rmtree(r)


def test_an_unknown_argument_kind_is_refused():
    r, cr = _tmp_repo(vocabulary=_path_vocab(odd=("read", {"accepts": "directory"})),
                      spec={"exec_allow": ["odd"]})
    out = cr.call_tool("run_command", {"command": "odd", "path": "sub"})
    assert out.startswith("ERROR:") and "unknown `accepts`" in out
    shutil.rmtree(r)


# --- T50: which CLONE this run is about -------------------------------------
# The target moved from the DECLARATION to the RUN, so these four cases are the whole claim:
# a vocabulary that names no clone needs no target, a real one resolves into a real cwd, a run
# that declared none is refused rather than defaulted, and a target that does not resolve is
# refused by the same two steps that have always guarded a `cwd`.

WHOAMI = "import os; print(os.getcwd())"


def _clone_vocab():
    """One entry that runs in the run's clone, spelled the way `.solar/commands.json` spells it."""
    return {"where": {"argv": [PY, "-c", WHOAMI], "kind": "read", "timeout": 30,
                       "cwd": f"repos/{CLONE}"}}


def test_a_vocabulary_that_names_no_clone_needs_no_target():
    """The rule is read from the DECLARATION, so an install with no clones is untouched by it."""
    assert clone_required(_vocab(peek=("print('ok')", "read"))) is False
    assert clone_required(_clone_vocab()) is True


def test_the_run_clone_resolves_into_a_real_cwd():
    r, cr = _tmp_repo(vocabulary=_clone_vocab(), spec={"exec_allow": ["where"]},
                      clone="alpha")
    (r / "repos" / "alpha").mkdir(parents=True)
    out = cr.call_tool("run_command", {"command": "where"})
    assert "cwd=repos" in out and "alpha" in out          # the record names the target it used
    assert str((r / "repos" / "alpha").resolve()).lower() in out.lower()   # and it ran THERE
    shutil.rmtree(r)


def test_a_run_that_declared_no_clone_is_refused_at_the_call():
    """Not defaulted, not guessed - and the message says what to do instead."""
    r, cr = _tmp_repo(vocabulary=_clone_vocab(), spec={"exec_allow": ["where"]})
    (r / "repos" / "alpha").mkdir(parents=True)
    out = cr.call_tool("run_command", {"command": "where"})
    assert out.startswith("ERROR:")
    assert "declared none" in out and "--clone" in out
    shutil.rmtree(r)


def test_one_vocabulary_serves_every_clone():
    """The point of the whole item: the SAME declaration runs in a different repository, so a
    role working on clone B cannot be handed a pass from clone A's checks."""
    r, _ = _tmp_repo(vocabulary=_clone_vocab())
    for name in ("alpha", "beta"):
        (r / "repos" / name).mkdir(parents=True)
    runs = {name: CommandRunner(r, {"exec_allow": ["where"]}, clone=name)
            .call_tool("run_command", {"command": "where"}).lower()
            for name in ("alpha", "beta")}
    assert str((r / "repos" / "alpha").resolve()).lower() in runs["alpha"]
    assert str((r / "repos" / "beta").resolve()).lower() in runs["beta"]
    assert str((r / "repos" / "beta").resolve()).lower() not in runs["alpha"]
    shutil.rmtree(r)


def test_the_word_for_no_clone_is_reserved_not_a_name():
    """`none` is a DECLARATION, so it cannot also be a clone's name - and a run that declared it
    gets its own reason at the call rather than "not a directory: repos/none"."""
    r, _ = _tmp_repo(vocabulary=_clone_vocab())
    (r / "repos" / "alpha").mkdir(parents=True)
    assert "touches NO clone" in clone_problem(r, CLONE_NONE, _clone_vocab())
    cr = CommandRunner(r, {"exec_allow": ["where"]}, clone=CLONE_NONE)
    out = cr.call_tool("run_command", {"command": "where"})
    assert out.startswith("ERROR:") and f"--clone {CLONE_NONE}" in out
    shutil.rmtree(r)


def test_a_target_that_does_not_resolve_is_refused_before_anything_runs():
    r, _ = _tmp_repo(vocabulary=_clone_vocab())
    (r / "repos" / "alpha").mkdir(parents=True)
    assert clone_problem(r, "alpha", _clone_vocab()) == ""
    assert "not a directory" in clone_problem(r, "nope", _clone_vocab())
    # **A NAME, not a path** - and this is the case that made the rule: `alpha/../..` resolves to
    # the ROOT itself, which exists, so the escape test and the is-a-directory test both pass it
    # and the command would run in the root while the record said a clone.
    assert "plain directory name" in clone_problem(r, "../../etc", _clone_vocab())
    assert "plain directory name" in clone_problem(r, "alpha/../..", _clone_vocab())
    shutil.rmtree(r)


def test_the_clone_reaches_the_command_layer_through_the_executor():
    """The parameter is on `executor.run` and must arrive at the runner it builds - the hop a
    signature change can silently drop."""
    import inspect

    from solar_governor import executor
    sig = inspect.signature(executor.run)
    assert sig.parameters["clone"].default == ""
    src = inspect.getsource(executor.run)
    assert "clone=clone" in src          # the one call site that builds the runner
    assert sig.parameters["target"].default is None    # the OTHER target, still the model endpoint


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"all {len(fns)} command tests passed")
