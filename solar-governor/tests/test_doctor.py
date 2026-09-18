"""`doctor` must report the thing it can see, and not claim more than that.

Two checks are covered here, both from v5.6.2 and both the same defect class: a report
whose wording invites a wrong reading.
  - `registry` said "10 specialists" for a repo that declares 7. The count was the
    MERGED, dispatchable set (built-ins included), so the number was right and the
    word was missing. Both numbers are now named.
  - the `runner` check described `stub` as "no API key -> deterministic stub", which
    stopped being the whole truth once a selected stub is honoured by request; and it
    reported PASS for a selected `http` with no key, i.e. for a run that will not
    happen as described.

Offline: no key is set, so `_model_check` never probes the provider.
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.pop("SOLAR_API_KEY", None)
os.environ.pop("DEEPSEEK_API_KEY", None)
os.environ.pop("SOLAR_RUNNER", None)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solar_governor import cli                      # noqa: E402
from solar_governor.core import Config              # noqa: E402


def _repo(declared: dict, runner: str = "") -> Path:
    r = Path(tempfile.mkdtemp(prefix="solar-doctor-"))
    (r / ".solar").mkdir(parents=True, exist_ok=True)
    (r / ".solar" / "registry.json").write_text(json.dumps(declared), encoding="utf-8")
    Config(repo=str(r), runner=runner).save(r / ".solar" / "config.json")
    return r


def _doctor(root: Path, capsys) -> dict:
    cli.cmd_doctor(argparse.Namespace(repo=str(root), json=True))
    return json.loads(capsys.readouterr().out)


def _seven_roles() -> dict:
    return {f"role-{i}": {"role": f"Role {i}", "system": "You do the thing.",
                          "tools": ["workspace"]} for i in range(7)}


def test_doctor_separates_declared_roles_from_dispatchable_ones(capsys):
    """7 declared + 3 built-in = 10 that can be dispatched. Reporting only the union
    reads as a defect, reporting only the file understates what works."""
    root = _repo(_seven_roles())
    try:
        checks = _doctor(root, capsys)
        assert checks["registry"]["status"] == "PASS"
        assert checks["registry"]["detail"].startswith(
            "10 dispatchable (7 declared + 3 built-in)")
    finally:
        shutil.rmtree(root)


def test_a_repo_that_declares_nothing_extra_gets_no_arithmetic(capsys):
    """With nothing merged the two numbers are equal, and "(3 declared + 0 built-in)"
    would be noise rather than information."""
    root = _repo({})
    try:
        detail = _doctor(root, capsys)["registry"]["detail"]
        assert detail.startswith("3 dispatchable")
        assert "declared" not in detail
    finally:
        shutil.rmtree(root)


def test_doctor_warns_when_the_selected_runner_cannot_run(capsys):
    """`http` without a key still falls back to the stub. Saying PASS and describing
    provider calls would describe a run that is not going to happen."""
    root = _repo(_seven_roles(), runner="http")
    try:
        check = _doctor(root, capsys)["runner"]
        assert check["status"] == "WARN"
        assert "SOLAR_API_KEY" in check["detail"]
    finally:
        shutil.rmtree(root)


def test_an_explicit_stub_runner_is_reported_as_a_choice_not_a_fallback(capsys):
    root = _repo(_seven_roles(), runner="stub")
    try:
        check = _doctor(root, capsys)["runner"]
        assert check["status"] == "PASS"
        assert "no provider call" in check["detail"]
    finally:
        shutil.rmtree(root)
