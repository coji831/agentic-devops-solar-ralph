"""Ledger tests: the record is appended, and content the runtime did not write survives.

The regression these exist for actually happened. `render()` replaced the whole file on
every run, and a real engagement kept a 115-line hand-written task brief at that path —
which an unrelated integration run destroyed. Every test below is a way that could
happen again.
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solar_governor import ledger                        # noqa: E402
from solar_governor.core import Config                   # noqa: E402

# a stand-in for the kind of document a human keeps in this file
CURATED = """## Objective

Record the fourth review round and fix a stale size figure in the handover.

## 1. THE SIZE FIGURE IS WRONG - fix it in the handover and the PR description

`tasks/0001-project-manual-reopen.md` -> `## Handover` currently says +317/-13.
"""


def _cfg() -> Config:
    return Config(repo=tempfile.mkdtemp(prefix="solar-ledger-"))


def _state(objective: str = "do the thing", stage: str = "complete",
           verdict: str = "APPROVED", decisions=None) -> dict:
    return {"objective": objective, "stage": stage, "verdict": verdict,
            "attempts": 1, "model": "stub", "work_queue": [],
            "decisions_log": decisions if decisions is not None else ["TASK_COMPLETE"]}


def test_the_first_record_creates_the_ledger():
    cfg = _cfg()
    path, action = ledger.record(cfg, _state("first task"), "t1")
    text = path.read_text(encoding="utf-8")
    assert action == "created"
    assert ledger.HEADER in text
    assert "first task" in text and ledger.END in text
    shutil.rmtree(cfg.root)


def test_a_second_run_appends_and_the_first_survives():
    cfg = _cfg()
    ledger.record(cfg, _state("first task"), "t1")
    path, action = ledger.record(cfg, _state("second task"), "t2")
    text = path.read_text(encoding="utf-8")
    assert action == "appended"
    assert "first task" in text and "second task" in text
    assert text.count(ledger.BEGIN) == 2
    shutil.rmtree(cfg.root)


def test_the_same_run_stepping_again_updates_its_own_section():
    """A run that steps three times must leave ONE section, not three half-finished ones."""
    cfg = _cfg()
    ledger.record(cfg, _state("work", stage="specialist", verdict=""), "t1")
    path, action = ledger.record(cfg, _state("work", stage="complete"), "t1")
    text = path.read_text(encoding="utf-8")
    assert action == "updated"
    assert text.count(ledger.BEGIN) == 1
    assert "stage: complete" in text
    assert "stage: specialist" not in text
    shutil.rmtree(cfg.root)


def test_hand_written_prose_at_the_ledger_path_is_never_touched():
    """THE REGRESSION. This is how a real task brief was destroyed."""
    cfg = _cfg()
    cfg.ledger_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.ledger_path.write_text(CURATED, encoding="utf-8")
    path, action = ledger.record(cfg, _state("an unrelated integration run"), "a-inv6")
    text = path.read_text(encoding="utf-8")
    assert action == "appended"
    assert CURATED.strip() in text            # byte-for-byte, not merely "still there"
    assert "an unrelated integration run" in text
    shutil.rmtree(cfg.root)


def test_prose_AFTER_a_section_survives_that_section_being_updated():
    """The case a naive parser gets wrong: trailing prose looks like part of the section."""
    cfg = _cfg()
    ledger.record(cfg, _state("work"), "t1")
    with cfg.ledger_path.open("a", encoding="utf-8") as fh:
        fh.write("\n## Notes added by hand after the run\n\nKeep this.\n")
    path, action = ledger.record(cfg, _state("work", stage="reworked"), "t1")
    text = path.read_text(encoding="utf-8")
    assert action == "updated"
    assert "Keep this." in text
    assert "stage: reworked" in text
    shutil.rmtree(cfg.root)


def test_sections_are_matched_by_thread_not_by_position():
    cfg = _cfg()
    ledger.record(cfg, _state("run one"), "alpha")
    ledger.record(cfg, _state("run two"), "beta")
    path, action = ledger.record(cfg, _state("run one again", stage="reworked"), "alpha")
    text = path.read_text(encoding="utf-8")
    assert action == "updated"
    assert "run two" in text                      # the other run is untouched
    assert "run one again" in text
    assert text.count(ledger.BEGIN) == 2
    assert text.index("run one again") < text.index("run two")
    shutil.rmtree(cfg.root)


def test_an_unterminated_section_is_kept_as_text():
    """A half-written section must not become a hole that swallows the next run."""
    cfg = _cfg()
    cfg.ledger_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.ledger_path.write_text(f"{ledger.BEGIN} t1 | cut off mid-write\nbody without an end\n",
                               encoding="utf-8")
    path, _ = ledger.record(cfg, _state("a later run"), "t2")
    text = path.read_text(encoding="utf-8")
    assert "cut off mid-write" in text and "a later run" in text
    shutil.rmtree(cfg.root)


def test_rendering_is_idempotent():
    """Bytes must stabilise, or every run would show a spurious diff."""
    cfg = _cfg()
    ledger.record(cfg, _state("one"), "t1")
    ledger.record(cfg, _state("two"), "t2")
    text = cfg.ledger_path.read_text(encoding="utf-8")
    assert ledger.render(ledger.tokenize(text)) == text
    shutil.rmtree(cfg.root)


def test_tokenize_keeps_prose_in_order_around_sections():
    cfg = _cfg()
    cfg.ledger_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.ledger_path.write_text(CURATED, encoding="utf-8")
    ledger.record(cfg, _state("middle run"), "t1")
    tokens = ledger.tokenize(cfg.ledger_path.read_text(encoding="utf-8"))
    kinds = [t[0] for t in tokens]
    assert kinds == ["text", "section"]
    assert "THE SIZE FIGURE IS WRONG" in tokens[0][1]
    shutil.rmtree(cfg.root)
