"""TD-5.6-6: a fresh start on a re-used thread must not inherit the last run.

`work_queue`, `decisions_log`, `tokens_in`, `tokens_out`, `tool_calls` and `node_ms`
are all `operator.add` channels, so invoking over an existing checkpoint APPENDS to the
previous run's values. The default thread is a fixed `t1`, which made the polluted
state the NORMAL path rather than an edge case.

The counter-constraint is what these tests exist for: `run --json` followed by
`--approve` must still resume the SAME thread. So the reset is scoped to a start with
no pending interrupt, and `test_a_resume_continues_instead_of_starting_clean` is the
guard that keeps it scoped.

**v5.7.4 adds `node_ms`,** and it is a reducer that has to survive a RESUME for the
opposite reason `tokens_in` has to be cleared on a fresh start: a run driven step by step
with `--result` is several CLI invocations, so the run's clock only exists if the
checkpoint carries it. Both directions are asserted below.

Offline deterministically: no key, therefore the stub runner, therefore no network.
"""
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

os.environ.pop("SOLAR_API_KEY", None)
os.environ.pop("DEEPSEEK_API_KEY", None)
os.environ.pop("SOLAR_MODEL", None)
os.environ.pop("SOLAR_RUNNER", None)     # an ambient runner would change what runs

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solar_governor import graph, runcard                # noqa: E402
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


def test_the_transcript_channel_is_written_into_the_state_db():
    """`T10` (2026-09-23): the transcript is TELEMETRY, and telemetry here means it rides the state
    DB the checkpointer already writes rather than a table of its own - `05` section 4 forbids a
    fifth sink, and section 5's ruling is that this store is per-machine and never citable.

    **A stub run makes no tool calls, so what this asserts is the MECHANISM, not a populated row:**
    the channel exists in `writes`, keyed by the thread. That a call produces a row with a tool name
    and a target is `test_executor.py`'s subject, and the two are the two halves of one claim.
    """
    repo = _tmp_repo()
    try:
        cfg = _cfg(repo)
        run_task(cfg, "refactor the API layer", thread="t-transcript")
        # **`with sqlite3.connect(...)` does NOT close the connection** - it commits or rolls back
        # and leaves the handle open, so on Windows the `rmtree` below fails with `WinError 32`
        # and the test reads as a failure of the thing it just proved. Closed explicitly.
        db = sqlite3.connect(cfg.checkpoint_path)
        try:
            row = db.execute("SELECT COUNT(*) FROM writes WHERE channel = 'tool_transcript'")
            total = row.fetchone()[0]
        finally:
            db.close()
        assert total >= 1, f"tool_transcript never reached {cfg.checkpoint_path.name}"
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


# --------------------------------------------------------------------------- v5.7.4
#
# The run's own clock. `_timed` is the only reader of `time` in `graph.py`, so replacing
# the module on `graph` isolates the clock completely - and an exact millisecond is only
# assertable against a clock a test can drive.

class _AdvancingClock:
    """Advances a fixed amount per read, so an assertion can name the millisecond."""

    def __init__(self, step: float) -> None:
        self.step = step
        self.now = 0.0

    def perf_counter(self) -> float:
        self.now += self.step
        return self.now


def test_the_run_clock_contributes_only_its_own_slice(monkeypatch):
    """The unit of the change, and the trap beside it. `_timed` reports THIS node's clock
    and nothing else: `node_ms` is an `operator.add` channel, so adding the incoming
    value here as well would total the run twice. One place sums, and it is the reducer â€”
    which is why the graph-level test below is the one that can prove accumulation."""
    monkeypatch.setattr(graph, "time", _AdvancingClock(step=0.250))
    assert graph._timed("a", lambda state: {})({})["node_ms"] == 250

    carried = graph._timed("b", lambda state: {"verdict": "APPROVED"})({"node_ms": 9999})
    assert carried["node_ms"] == 250, "the incoming total is the reducer's business, not ours"
    assert carried["verdict"] == "APPROVED", "a node's own return is passed through untouched"


def test_the_run_clock_totals_a_resumed_run(monkeypatch):
    """v5.7.4's whole point. Two CLI invocations on one thread: the first reaches the
    review interrupt (material_gate, dispatch, specialist -> three slices), the second
    resumes it (review, complete -> two more). The card's `duration_ms` sees only the last
    invocation; this sees 5 slices.

    That the interrupting `review` adds NOTHING is asserted by the first number: its work
    is thrown away and re-done on resume, so counting it would charge twice for one node.
    """
    monkeypatch.setattr(graph, "time", _AdvancingClock(step=0.250))
    repo = _tmp_repo()
    try:
        cfg = _cfg(repo, approval=True)
        paused = run_step(cfg, "refactor the API layer", thread="t2")
        assert "__interrupt__" in paused
        assert paused["node_ms"] == 750, "three timed nodes; the interrupted one adds none"

        resumed = run_step(cfg, "refactor the API layer", thread="t2", resume="approve")
        assert "__interrupt__" not in resumed
        assert resumed["node_ms"] == 1250, "the resume added its own two nodes' clocks"
    finally:
        shutil.rmtree(repo)


def test_the_run_clock_does_not_leak_into_a_fresh_start(monkeypatch):
    """It is a reducer, so it inherits across a re-used thread exactly as `tokens_in`
    does. TD-5.6-6's reset is what stops it, and this proves the reset covers the new
    channel rather than only the ones that existed when it was written."""
    monkeypatch.setattr(graph, "time", _AdvancingClock(step=0.250))
    repo = _tmp_repo()
    try:
        cfg = _cfg(repo)
        first = run_task(cfg, "refactor the API layer", thread="t1")
        second = run_task(cfg, "add a login feature with tests", thread="t1")
        assert first["node_ms"] == 1250, "five nodes on a fresh thread"
        assert second["node_ms"] == 1250, "...and the second run starts from zero too"
    finally:
        shutil.rmtree(repo)


def test_the_card_carries_the_run_clock_and_nulls_it_when_nothing_was_timed():
    """`runcard.write` is called from five places, including error paths that pass a state
    no node ever touched. `null` is the difference between "never timed" and "took 0 ms",
    which is the same asymmetry `tokens.reported` closes for `0/0` (TD-5.6-12).

    `duration_ms` stays: it is a real reading of a different thing, and every card already
    on disk means it.
    """
    repo = _tmp_repo()
    try:
        cfg = _cfg(repo)
        timed = runcard.write(cfg, {"thread": "t-card", "objective": "x",
                                    "node_ms": 1234}, "t-card", time.time())
        card = json.loads(timed.read_text(encoding="utf-8"))
        assert card["node_ms"] == 1234
        assert card["duration_ms"] >= 0, "the invocation clock is still there"

        untimed = runcard.write(cfg, {"thread": "t-card2", "objective": "x"},
                                "t-card2", time.time())
        dropped = json.loads(untimed.read_text(encoding="utf-8"))
        assert dropped["node_ms"] is None
        assert dropped["duration_ms"] >= 0
    finally:
        shutil.rmtree(repo)
