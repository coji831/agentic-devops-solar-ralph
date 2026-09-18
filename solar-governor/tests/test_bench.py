"""Offline tests for `bench` (TD-5.7-6): it must leave evidence, and must not claim a
score it does not have.

The measured defect: two `bench --n 2` runs printed `2/2 passed`, wrote **no run-cards**
(`.solar/runs/` stayed empty) and kept no answer, while the model had answered one of
three questions wrong. "passed" was `stage=complete + verdict=APPROVED`, which with
`human_approval: false` is the graph approving *itself*.

These tests pin the three parts of the fix: one run-card per repetition, the answer (with
its length and hash) in every row, and a name for the count that cannot be read as
"answered correctly". `run_task` is patched throughout — the instrument is the subject
here, and a real endpoint would make the test's own numbers the thing under test.
"""
import hashlib
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solar_governor import bench, runcard                # noqa: E402
from solar_governor.core import Config                   # noqa: E402


@pytest.fixture(autouse=True)
def _hermetic_env(monkeypatch):
    """Own the environment: `run --runner X` sets `SOLAR_RUNNER` process-wide and never
    restores it (TD-5.6-13), and env beats config BY DESIGN — so a leaked value would
    silently change which runner these tests resolve."""
    for name in ("SOLAR_RUNNER", "SOLAR_API_KEY", "SOLAR_MODEL", "SOLAR_BASE_URL"):
        monkeypatch.delenv(name, raising=False)
    yield


def _tmp_repo(runner: str = "http") -> Path:
    r = Path(tempfile.mkdtemp(prefix="solar-bench-"))
    (r / ".solar").mkdir(parents=True)
    cfg = Config(repo=str(r), runner=runner)
    cfg.save(r / ".solar" / "config.json")
    reg = {"investigator": {"role": "Investigator", "system": "You research.",
                            "tools": [], "next_edges": [], "model": ""}}
    (r / ".solar" / "registry.json").write_text(json.dumps(reg), encoding="utf-8")
    return r


def _state(output: str, verdict: str = "APPROVED") -> dict:
    """The state shape `run_task` returns for a finished run."""
    return {"stage": "complete", "verdict": verdict, "role": "Investigator",
            "model": "solar-local:latest", "provider": "127.0.0.1:11434",
            "attempts": 1, "tokens_in": 100, "tokens_out": 20, "tool_calls": 2,
            "output": output, "decisions_log": [], "usage_reported": True}


def _answer_for(*a, **k) -> dict:
    return _state(f"answer for {k['thread']}")


# ---------------------------------------------------------------------------
# the evidence: a card per repetition, and the answer in the row
# ---------------------------------------------------------------------------

def test_every_repetition_leaves_a_run_card(monkeypatch):
    r = _tmp_repo()
    monkeypatch.setattr(bench, "run_task", _answer_for)
    try:
        agg = bench.run(str(r), "say hello", n=2)
        cards = sorted((r / ".solar" / "runs").glob("*.json"))
        assert len(cards) == 2, "a repetition with no card is a claim with nothing behind it"
        written = [json.loads(c.read_text(encoding="utf-8")) for c in cards]
        assert agg["cards"] == [str(c) for c in cards]
    finally:
        shutil.rmtree(r)
    # each card answers for its OWN run — a card that cannot be tied to a row is not evidence
    for card in written:
        assert card["output"] == f"answer for {card['thread']}"
    assert len({c["thread"] for c in written}) == 2


def test_a_row_carries_the_answer_its_length_and_its_hash(monkeypatch):
    r = _tmp_repo()
    answer = "The oldest commit is 1a2b3c4."
    monkeypatch.setattr(bench, "run_task", lambda *a, **k: _state(answer))
    try:
        agg = bench.run(str(r), "say hello", n=1)
        row = agg["rows"][0]
        assert row["output"] == answer
        assert row["output_chars"] == len(answer)
        assert row["output_sha256"] == hashlib.sha256(answer.encode("utf-8")).hexdigest()[:16]
        assert Path(row["run_card"]).is_file()
    finally:
        shutil.rmtree(r)


def test_two_runs_that_answer_differently_can_be_told_apart(monkeypatch):
    """The point of the local-vs-cloud bench: compare answers, not just count them."""
    r = _tmp_repo()
    answers = iter(["the oldest commit is 1a2b3c4", "the oldest commit is deadbeef"])
    monkeypatch.setattr(bench, "run_task", lambda *a, **k: _state(next(answers)))
    try:
        agg = bench.run(str(r), "say hello", n=2)
    finally:
        shutil.rmtree(r)
    first, second = agg["rows"]
    assert first["output"] != second["output"]
    assert first["output_sha256"] != second["output_sha256"]


# ---------------------------------------------------------------------------
# the name: approval is not correctness
# ---------------------------------------------------------------------------

def test_the_count_cannot_be_read_as_correctness(monkeypatch, capsys):
    """Reproduce the measured defect: the answer is wrong and the run is still approved."""
    r = _tmp_repo()
    monkeypatch.setattr(bench, "run_task",
                        lambda *a, **k: _state("WRONG: the oldest commit is 9f8e7d6"))
    try:
        agg = bench.run(str(r), "say hello", n=2)
    finally:
        shutil.rmtree(r)
    printed = capsys.readouterr().out

    # the approval is real, and is reported under a name that cannot be read as a score
    assert (agg["approved"], agg["not_approved"]) == (2, 0)
    assert "passed" not in agg and "passed" not in printed
    assert "not a check of the answer" in printed
    assert "solar-governor eval" in printed     # and where a real check comes from


def test_a_run_that_failed_is_not_approved(monkeypatch):
    """The other half of the count: carrying an error is not an approval."""
    r = _tmp_repo()

    def failed(*a, **k):
        state = _state("partial answer", verdict="REJECTED")
        state["error"] = "max_rounds"
        return state

    monkeypatch.setattr(bench, "run_task", failed)
    try:
        agg = bench.run(str(r), "say hello", n=1)
    finally:
        shutil.rmtree(r)
    assert (agg["approved"], agg["not_approved"]) == (0, 1)
    assert agg["rows"][0]["error"] == "max_rounds"


# ---------------------------------------------------------------------------
# the edges: a failure is a row, an impossible bench is refused
# ---------------------------------------------------------------------------

def test_a_provider_failure_is_a_row_not_a_lost_run(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(bench, "run_task", boom)
    r = _tmp_repo()
    try:
        agg = bench.run(str(r), "say hello", n=2)
    finally:
        shutil.rmtree(r)
    assert (agg["approved"], agg["not_approved"]) == (0, 2)
    assert agg["rows"][0]["stage"] == "error"
    assert "connection refused" in agg["rows"][0]["error"]
    assert agg["cards"] == [] and len(agg["errors"]) == 2


def test_an_aggregate_over_no_runs_is_refused():
    with pytest.raises(SystemExit):
        bench.run(".", "say hello", n=0)


def test_a_runner_that_cannot_measure_is_refused():
    r = _tmp_repo(runner="stub")
    try:
        with pytest.raises(SystemExit):
            bench.run(str(r), "say hello", n=1)
    finally:
        shutil.rmtree(r)


# ---------------------------------------------------------------------------
# the card carries the answer (runcard, v5.7.3)
# ---------------------------------------------------------------------------

def _card(repo: Path, thread: str, output: str) -> dict:
    path = runcard.write(Config(repo=str(repo), runner="http"),
                         {"stage": "complete", "output": output, "decisions_log": []},
                         thread, time.time())
    return json.loads(path.read_text(encoding="utf-8"))


def test_the_card_carries_the_answer():
    r = _tmp_repo()
    answer = "Line one.\nLine two, with punctuation."
    try:
        card = _card(r, "t-answer", answer)
    finally:
        shutil.rmtree(r)
    # byte-identical: a cap that changes ordinary answers is a cap that gets reverted
    assert card["output"] == answer


def test_a_very_long_answer_is_capped_and_says_so():
    r = _tmp_repo()
    huge = "x" * (runcard.MAX_OUTPUT_CHARS + 500)
    try:
        card = _card(r, "t-big", huge)
    finally:
        shutil.rmtree(r)
    assert "elided" in card["output"], "a truncated answer must not read as a short one"
    assert str(len(huge)) in card["output"]
    assert len(card["output"]) < len(huge)
