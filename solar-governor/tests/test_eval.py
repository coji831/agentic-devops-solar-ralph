"""Offline tests for the eval battery + tool-output truncation knob."""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solar_governor import eval as ev               # noqa: E402
from solar_governor import executor                 # noqa: E402
from solar_governor.core import Config              # noqa: E402


def _tmp_repo() -> Path:
    r = Path(tempfile.mkdtemp(prefix="solar-eval-"))
    (r / ".solar").mkdir(parents=True)
    cfg = Config(repo=str(r), runner="http")
    cfg.save(r / ".solar" / "config.json")
    cfg.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    reg = {"investigator": {"role": "Investigator", "system": "You research.",
                            "tools": [], "next_edges": [], "model": ""}}
    (r / ".solar" / "registry.json").write_text(json.dumps(reg), encoding="utf-8")
    return r


def test_check_substrings():
    assert ev.check("the answer is a b and six routes",
                    {"must_contain": ["a b", "six"]}) is True
    assert ev.check("a b", {"must_contain": ["c"]}) is False
    assert ev.check("has forbidden", {"not_contain": ["forbidden"]}) is False
    assert ev.check("A B", {"must_contain": ["a"]}) is True     # case-insensitive


def test_tool_output_cap():
    os.environ["SOLAR_TOOL_OUTPUT_CHARS"] = "10"
    try:
        capped = executor._cap_tool("x" * 500)
        assert len(capped) <= 10 + 80 and "truncated" in capped
        assert executor._cap_tool("short") == "short"
        os.environ["SOLAR_TOOL_OUTPUT_CHARS"] = "0"
        assert executor._cap_tool("x" * 500) == "x" * 500        # unlimited
    finally:
        os.environ.pop("SOLAR_TOOL_OUTPUT_CHARS", None)


def test_eval_patched_pass():
    r = _tmp_repo()
    orig = executor.run
    executor.run = lambda *a, **k: {"output": "cn returns: a b", "usage": {"in": 5, "out": 5},
                                    "tool_calls": 0, "error": None, "model": "stub"}
    try:
        agg = ev.run(str(r), cases=[{"id": "cn-join", "role": "investigator",
                                     "objective": "what does cn return",
                                     "must_contain": ["a b"]}], n=1)
    finally:
        executor.run = orig
    assert agg["rows"][0]["pass"] is True
    assert agg["passed"] == 1
    shutil.rmtree(r)


if __name__ == "__main__":
    for fn in (test_check_substrings, test_tool_output_cap, test_eval_patched_pass):
        fn()
        print(f"PASS {fn.__name__}")
    print("all eval tests passed")
