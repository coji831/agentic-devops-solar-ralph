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


def test_eval_cases_resolution_order():
    """TD-5.4-4: explicit path > <repo>/.solar/eval-cases.json > built-ins."""
    r = _tmp_repo()
    cases, source = ev.load_cases(r)
    assert cases is ev.DEFAULT_CASES and source == "built-in defaults"

    per_repo = [{"id": "x", "role": "investigator", "objective": "o",
                 "must_contain": ["y"]}]
    (r / ".solar" / "eval-cases.json").write_text(json.dumps(per_repo), encoding="utf-8")
    cases, source = ev.load_cases(r)
    assert cases == per_repo and source == ev.CASES_FILE

    explicit = r / "custom.json"
    explicit.write_text(json.dumps(per_repo + [{"id": "z", "role": "investigator",
                                                "objective": "o",
                                                "must_contain": ["q"]}]),
                        encoding="utf-8")
    cases, source = ev.load_cases(r, str(explicit))
    assert len(cases) == 2 and source == str(explicit)
    shutil.rmtree(r)


def test_eval_warns_when_the_built_in_battery_does_not_apply():
    """A wrong signal is worse than no signal: 0% would be read as "harness broken"."""
    r = _tmp_repo()
    assert "NOT a signal" in ev.battery_warning(r, "built-in defaults")
    # a battery that belongs to the repo needs no warning
    assert ev.battery_warning(r, ev.CASES_FILE) == ""
    # ...nor does the repo the built-ins actually describe
    probe = r / ev.PILOT_PROBE
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text("export const cn = () => '';\n", encoding="utf-8")
    assert ev.battery_warning(r, "built-in defaults") == ""
    shutil.rmtree(r)


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
