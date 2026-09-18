"""TD-5.6-6: a fresh start on a re-used thread must not inherit the last run.

`work_queue`, `decisions_log`, `tokens_in`, `tokens_out` and `tool_calls` are all
`operator.add` channels, so invoking over an existing checkpoint APPENDS to the
previous run's values. The default thread is a fixed `t1`, which made the polluted
state the NORMAL path rather than an edge case.

The counter-constraint is what these tests exist for: `run --json` followed by
`--approve` must still resume the SAME thread. So the reset is scoped to a start with
no pending interrupt, and `test_a_resume_continues_instead_of_starting_clean` is the
guard that keeps it scoped.

Offline deterministically: no key, therefore the stub runner, therefore no network.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.pop("SOLAR_API_KEY", None)
os.environ.pop("DEEPSEEK_API_KEY", None)
os.environ.pop("SOLAR_MODEL", None)
os.environ.pop("SOLAR_RUNNER", None)     # an ambient runner would change what runs

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solar_governor.core import Config                 # noqa: E402
from solar_governor.graph import pending_interrupt, run_step, run_task  # noqa: E402


def _tmp_repo() -> Path:
    return Path(tempfile.mkdtemp(prefix="solar-thread-"))


def _cfg(repo: Path, approval: bool = False) -> Config:
    cfg = Config(repo=str(repo), human_approval=approval)
    cfg.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.save(repo / ".solar" / "config.json")
    return cfg


def test_a_second_run_on_the_same_thread_does_not_inherit_the_first():
    """The defect as observed: one run-card showing two `T1` rows and a decisions log
    carrying the previous run's entries."""
    repo = _tmp_repo()
    try:
        cfg = _cfg(repo)
        first = run_task(cfg, "add a login feature with tests", thread="t1")
        second = run_task(cfg, "refactor the API layer", thread="t1")

        assert len(first["work_queue"]) == 1
        assert len(second["work_queue"]) == 1, "the work queue carried the previous run"
        assert second["objective"] == "refactor the API layer"
        assert second["role"] == "implementer"       # routed for THIS task
        # Nothing from the first run survives. Its route is the tell: "tests" sent it
        # to the tester, and this task must not be able to see that.
        assert not any("tester" in d for d in second["decisions_log"])
        # The one extra entry is the note saying the reset happened, and nothing else.
        assert len(second["decisions_log"]) == len(first["decisions_log"]) + 1
    finally:
        shutil.rmtree(repo)


def test_the_reset_is_visible_in_the_run_it_applies_to():
    """A background reset would be a state change nobody can see. The note that it
    happened is the first entry of the fresh run's own decisions log, so the ledger and
    the run-card say why their totals start from zero."""
    repo = _tmp_repo()
    try:
        cfg = _cfg(repo)
        run_task(cfg, "add a login feature with tests", thread="t1")
        second = run_task(cfg, "refactor the API layer", thread="t1")
        assert second["decisions_log"][0].startswith("fresh start on thread 't1'")
    finally:
        shutil.rmtree(repo)


def test_a_first_run_on_a_thread_is_untouched():
    """Nothing to clear means nothing is said: a virgin thread does no extra work and
    carries no reset note."""
    repo = _tmp_repo()
    try:
        cfg = _cfg(repo)
        first = run_task(cfg, "refactor the API layer", thread="t3")
        assert not any("fresh start" in d for d in first["decisions_log"])
        assert first["work_queue"][0]["task"] == "refactor the API layer"
    finally:
        shutil.rmtree(repo)


def test_a_resume_continues_instead_of_starting_clean():
    """The constraint that scopes the reset: `run --json` then `--approve` resumes the
    same thread. A resume is a CONTINUATION, so clearing would drop the checkpoint the
    resume depends on. Nothing may be cleared while an interrupt is pending."""
    repo = _tmp_repo()
    try:
        cfg = _cfg(repo, approval=True)
        paused = run_step(cfg, "refactor the API layer", thread="t2")
        assert "__interrupt__" in paused
        assert pending_interrupt(cfg, "t2") is not None

        resumed = run_step(cfg, "refactor the API layer", thread="t2", resume="approve")
        assert "__interrupt__" not in resumed
        assert resumed.get("verdict") == "APPROVED"
        # the paused run's own history is still there: the resume continued it
        assert len(resumed["decisions_log"]) >= len(paused["decisions_log"])
        assert len(resumed["work_queue"]) == 1
        assert not any("cleared the previous run" in d for d in resumed["decisions_log"])
    finally:
        shutil.rmtree(repo)
