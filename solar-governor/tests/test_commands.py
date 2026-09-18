"""Tests for the vetted command vocabulary (patch Part C) and the approval gate (Part D).

Two properties matter more than the features here:

1. A command that is not declared, or not GRANTED to the role, must not exist for that
   role. Absence is the containment - a rule asking the model to avoid a command is not.
2. There is no free-text command or argument field, so a vocabulary command cannot be
   turned into an arbitrary one.

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

from solar_governor.commands import CommandRunner, load_vocabulary  # noqa: E402

PY = sys.executable


def _tmp_repo(vocabulary: dict | None = None, spec: dict | None = None,
              human_approval: bool = False) -> tuple[Path, CommandRunner]:
    r = Path(tempfile.mkdtemp(prefix="solar-cmd-"))
    (r / ".solar").mkdir(parents=True)
    (r / "sub").mkdir()
    if vocabulary is not None:
        (r / ".solar" / "commands.json").write_text(json.dumps(vocabulary),
                                                    encoding="utf-8")
    return r, CommandRunner(r, spec, human_approval=human_approval)


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

def test_granted_command_runs_and_reports_exit_and_output():
    r, cr = _tmp_repo(vocabulary=_vocab(hello=("print('hello world')", "check")),
                      spec={"exec_allow": ["hello"]})
    out = cr.call_tool("run_command", {"command": "hello"})
    assert "[hello] exit 0" in out
    assert "hello world" in out
    assert "kind=check" in out
    shutil.rmtree(r)


def test_a_failing_command_is_reported_not_raised():
    """A checker that fails is the SIGNAL, not an exception - the node has to read it."""
    r, cr = _tmp_repo(vocabulary=_vocab(boom=("import sys; sys.exit(3)", "check")),
                      spec={"exec_allow": ["boom"]})
    out = cr.call_tool("run_command", {"command": "boom"})
    assert "[boom] exit 3" in out
    shutil.rmtree(r)


def test_stderr_is_surfaced():
    r, cr = _tmp_repo(vocabulary=_vocab(noisy=("import sys; print('bad', file=sys.stderr)", "check")),
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
                                          "kind": "check", "max_output": 200}},
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
    assert names == {"list_tree", "read_file", "glob", "run_command"}
    assert layer.call_tool("run_command", {"command": "peek"}).startswith("[peek] exit 0")
    assert layer.call_tool("nope", {}).startswith("ERROR: unknown tool")
    shutil.rmtree(r)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"all {len(fns)} command tests passed")
