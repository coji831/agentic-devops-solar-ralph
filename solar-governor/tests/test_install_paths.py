"""Two install-path defects found by live verification, and their guards (v5.6.3).

A) A repo with `.solar/config.json` but no `.solar/state/` crashed the `--json` path (and
   `serve`) with a bare `sqlite3.OperationalError`, while the interactive path worked. That
   state is exactly what a FRESH CLONE looks like, because `state/` is gitignored while
   `config.json` and `registry.json` are tracked.
B) A `config.json` carrying a UTF-8 BOM - what PowerShell 5.1's `Set-Content -Encoding utf8`
   or Notepad's "UTF-8 with BOM" produce - killed every command with a traceback and exit 1,
   a code outside the documented 0/2/10/11/12 contract.

The BOM fix is a SWEEP: every `.solar/` file a human may author is read through
`core.read_text`/`read_json`, so this file tests each of them rather than only config.json.
"""
import argparse
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.pop("SOLAR_API_KEY", None)
os.environ.pop("DEEPSEEK_API_KEY", None)
os.environ.pop("SOLAR_RUNNER", None)
os.environ.pop("SOLAR_MODEL", None)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solar_governor import __version__, cli, commands, executor, install  # noqa: E402
from solar_governor.core import Config                                     # noqa: E402
from solar_governor.eval import load_cases                                 # noqa: E402
from solar_governor.graph import pending_interrupt, run_step, run_task      # noqa: E402
from solar_governor.registry import declared, load as load_registry         # noqa: E402

BOM = b"\xef\xbb\xbf"


def _repo(config: str | None = None, *, raw: bytes | None = None,
          state: bool = False) -> Path:
    """A scratch repo. `state=False` is the fresh-clone shape: config tracked, state absent."""
    r = Path(tempfile.mkdtemp(prefix="solar-paths-"))
    (r / ".solar").mkdir(parents=True)
    body = config if config is not None else json.dumps(
        {"profile": "light", "model": "", "runner": "stub", "human_approval": False},
        indent=2)
    (r / ".solar" / "config.json").write_bytes(
        raw if raw is not None else body.encode("utf-8"))
    if state:
        (r / ".solar" / "state").mkdir(parents=True, exist_ok=True)
    return r


def _ns(repo: Path, **kw) -> argparse.Namespace:
    base = dict(repo=str(repo), thread="t1", task="probe the install path", chain=None,
                auto=False, role=None, approve=None, result=None, json=True, runner="stub")
    base.update(kw)
    return argparse.Namespace(**base)


# --- A) the missing state directory -------------------------------------------------

def test_json_path_works_on_a_fresh_clone_and_creates_the_state_dir():
    """The defect: `pending_interrupt` opened the checkpoint DB without ensuring its
    directory, so `--json` died on the very state a clone is in."""
    repo = _repo()
    try:
        assert not (repo / ".solar" / "state").exists()
        try:
            cli.cmd_run(_ns(repo))
        except SystemExit as e:
            assert e.code == cli.EXIT_OK, f"exit {e.code}, expected a clean run"
        else:
            raise AssertionError("cmd_run did not exit")
        assert (repo / ".solar" / "state").exists(), "the state dir was not created"
    finally:
        shutil.rmtree(repo)


def test_pending_interrupt_tolerates_a_missing_state_dir():
    repo = _repo()
    try:
        cfg = Config.load(repo / ".solar" / "config.json")
        assert pending_interrupt(cfg, "t1") is None      # and does not raise
    finally:
        shutil.rmtree(repo)


def test_both_graph_paths_agree_about_the_same_repo():
    """`run_task` worked and `run_step` did not, which is the real defect: two paths
    disagreeing about one repo."""
    repo = _repo()
    try:
        cfg = Config.load(repo / ".solar" / "config.json")
        state = run_task(cfg, "probe the install path", thread="t1")
        assert state.get("stage") == "complete"
        assert run_step(cfg, "a second task", thread="t2").get("stage") == "complete"
    finally:
        shutil.rmtree(repo)


def test_doctor_tests_creatability_not_existence():
    """`checkpoint-writable` tested whether `state/` EXISTS, so it reported FAIL for a
    fresh clone that runs perfectly well. It now tests whether the dir can be created."""
    repo = _repo()
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli.cmd_doctor(argparse.Namespace(repo=str(repo), json=True))
        checks = json.loads(buf.getvalue())
        assert checks["checkpoint-writable"]["status"] == "PASS"
    finally:
        shutil.rmtree(repo)


# --- B) the BOM sweep --------------------------------------------------------------

def test_config_with_a_bom_loads_and_runs():
    repo = _repo(raw=BOM + json.dumps(
        {"profile": "light", "model": "", "runner": "stub", "human_approval": False},
        indent=2).encode("utf-8"))
    try:
        cfg = Config.load(repo / ".solar" / "config.json")
        assert cfg.profile == "light"
        assert cfg.runner == "stub"
        try:
            cli.cmd_run(_ns(repo))
        except SystemExit as e:
            assert e.code == cli.EXIT_OK
        else:
            raise AssertionError("cmd_run did not exit")
    finally:
        shutil.rmtree(repo)


def test_registry_with_a_bom_still_declares_its_roles():
    repo = _repo()
    try:
        reg = {"frontend-engineer": {"role": "FE", "system": "You build UI.",
                                     "tools": ["workspace"]}}
        (repo / ".solar" / "registry.json").write_bytes(
            BOM + json.dumps(reg).encode("utf-8"))
        path = repo / ".solar" / "registry.json"
        assert "frontend-engineer" in load_registry(path)
        assert declared(path) == ["frontend-engineer"]
    finally:
        shutil.rmtree(repo)


def test_commands_vocabulary_with_a_bom_still_loads():
    repo = _repo()
    try:
        vocab = {"peek": {"argv": ["echo", "hi"], "desc": "say hi"}}
        (repo / ".solar" / "commands.json").write_bytes(
            BOM + json.dumps(vocab).encode("utf-8"))
        assert "peek" in commands.load_vocabulary(repo)
    finally:
        shutil.rmtree(repo)


def test_version_marker_with_a_bom_does_not_report_phantom_drift():
    """Without this, the marker compared as '\\ufeff5.6.2' and doctor warned about a
    mismatch with itself."""
    repo = _repo()
    try:
        (repo / ".solar" / "VERSION").write_bytes(BOM + f"{__version__}\n".encode("utf-8"))
        assert install.read_version(repo) == __version__
        status, detail = install.version_status(repo)
        assert status == "PASS", detail
    finally:
        shutil.rmtree(repo)


def test_per_repo_eval_cases_with_a_bom_load():
    repo = _repo()
    try:
        cases = [{"id": "cn-join", "objective": "join two tables", "expect": ["join"]}]
        (repo / ".solar" / "eval-cases.json").write_bytes(
            BOM + json.dumps(cases).encode("utf-8"))
        loaded, source = load_cases(repo)
        assert [c["id"] for c in loaded] == ["cn-join"]
        assert source == ".solar/eval-cases.json"
    finally:
        shutil.rmtree(repo)


def test_a_result_file_written_with_a_bom_does_not_leak_it_into_the_output():
    repo = _repo()
    try:
        result = repo / "handoff.result.md"
        result.write_bytes(BOM + b"specialist says: done\n")
        text = executor.resolve_result(str(result), repo)
        assert text.startswith("specialist says"), repr(text[:12])
        assert "\ufeff" not in text
    finally:
        shutil.rmtree(repo)


# --- the exit contract -------------------------------------------------------------

def test_an_unreadable_config_exits_with_the_documented_code():
    """It used to escape as a traceback and exit 1, which no wrapper handles."""
    repo = _repo(raw=b'{"profile": "light",,}')
    try:
        try:
            cli.cmd_run(_ns(repo))
        except SystemExit as e:
            assert e.code == cli.EXIT_USAGE == 2
        else:
            raise AssertionError("cmd_run did not exit")
    finally:
        shutil.rmtree(repo)
