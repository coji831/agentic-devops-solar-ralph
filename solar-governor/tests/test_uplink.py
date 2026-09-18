"""Offline tests for the hub uplink (TD-5.4-5) — opt-in, push-only, safe to fail.

No hub is contacted: the unreachable case points at a closed local port, and the
disabled case never leaves the process.
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solar_governor import uplink                        # noqa: E402
from solar_governor.core import Config                   # noqa: E402


def _cfg(value: str) -> Config:
    r = Path(tempfile.mkdtemp(prefix="solar-uplink-"))
    return Config(repo=str(r), uplink=value)


def test_endpoint_validation():
    assert uplink.endpoint("") == ("", "")
    assert uplink.endpoint("none") == ("", "")
    url, err = uplink.endpoint("hub:https://hub.example.com/")
    assert url == "https://hub.example.com" and err == ""
    url, err = uplink.endpoint("https://hub.example.com")
    assert url == "" and "unknown uplink" in err
    url, err = uplink.endpoint("hub:ftp://x")
    assert url == "" and "http(s)" in err


def test_disabled_uplink_is_a_noop():
    cfg = _cfg("none")
    assert uplink.push(cfg, {"verdict": "APPROVED"}, "t1") == ""
    assert uplink.status(cfg) == ("PASS", "none (local-only)")
    shutil.rmtree(cfg.root)


def test_doctor_status_fails_on_a_malformed_value():
    cfg = _cfg("hub:not-a-url")
    status, detail = uplink.status(cfg)
    assert status == "FAIL" and "http(s)" in detail
    shutil.rmtree(cfg.root)


def test_push_degrades_gracefully_when_the_hub_is_unreachable():
    """A hub that is down must not fail a run - and must not raise."""
    cfg = _cfg("hub:http://127.0.0.1:9")
    line = uplink.push(cfg, {"verdict": "APPROVED"}, "t1", timeout=1.0)
    assert line.startswith("uplink: skipped")
    shutil.rmtree(cfg.root)


def test_a_malformed_uplink_reports_rather_than_raising():
    cfg = _cfg("nonsense")
    assert uplink.push(cfg, {}, "t1").startswith("uplink: skipped (unknown uplink")
    shutil.rmtree(cfg.root)


def test_digest_carries_the_run_not_a_copy_of_the_work_product():
    state = {"role": "investigator", "verdict": "APPROVED", "output": "x" * 5000,
             "objective": "y" * 900, "error": "e" * 900,
             "decisions_log": [f"d{i}" for i in range(50)], "tokens_in": 10}
    d = uplink.digest(state, "t1", "some-repo")
    assert d["output_chars"] == 5000        # the length, never the content
    assert "output" not in d
    assert len(d["objective"]) == uplink.FIELD_CAP
    assert len(d["error"]) == uplink.FIELD_CAP
    assert len(d["decisions"]) == uplink.DECISION_CAP
    assert d["repo"] == "some-repo" and d["verdict"] == "APPROVED"
