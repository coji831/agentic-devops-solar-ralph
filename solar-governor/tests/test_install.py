"""Offline tests for the install surface: portable config, version marker, ignore block.

Grounded in two real engagements that drifted apart (2026-09-19): they had OPPOSITE
`.gitignore` rules for `.solar/config.json`, and the one that ignored it is the one where
a non-existent model id sat unreviewed for days.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solar_governor import __version__, install       # noqa: E402
from solar_governor.core import Config                # noqa: E402


def _repo(gitignore: str | None = None) -> Path:
    r = Path(tempfile.mkdtemp(prefix="solar-install-"))
    if gitignore is not None:
        (r / ".gitignore").write_text(gitignore, encoding="utf-8")
    return r


def _write_cfg(root: Path, payload: dict) -> Path:
    path = root / ".solar" / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# --- portable config ---------------------------------------------------------

def test_root_is_derived_from_the_config_location():
    """A config with no `repo` points at the repo it lives in, wherever that is."""
    r = _repo()
    path = _write_cfg(r, {"profile": "light", "model": "deepseek-flash"})
    cfg = Config.load(path)
    assert cfg.root == r.resolve()
    assert cfg.repo == ""
    shutil.rmtree(r)


def test_an_explicit_repo_still_wins():
    r = _repo()
    cfg = Config.load(_write_cfg(r, {"repo": str(r.parent)}))
    assert cfg.root == r.parent.resolve()
    shutil.rmtree(r)


def test_a_saved_config_contains_nothing_machine_specific():
    """The whole point: a config that can be committed in EVERY repo, because a stale
    model pin has to be able to show up in a diff."""
    r = _repo()
    path = r / ".solar" / "config.json"
    cfg = Config(model="deepseek-flash", runner="http")
    cfg.save(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert "repo" not in raw and "loaded_from" not in raw
    assert str(r) not in path.read_text(encoding="utf-8")
    # and it round-trips to the same root, derived this time
    assert Config.load(path).root == r.resolve()
    shutil.rmtree(r)


def test_merge_keeps_what_the_repo_chose_and_adds_what_is_new():
    existing = {"model": "deepseek-flash", "runner": "http", "repo": "C:\\elsewhere"}
    fresh = {"model": "", "runner": "", "model_tier": "", "uplink": "none"}
    merged = install.merge_config(existing, fresh)
    assert merged["model"] == "deepseek-flash"    # the repo's choice survives a re-init
    assert merged["runner"] == "http"
    assert merged["repo"] == "C:\\elsewhere"
    assert merged["model_tier"] == ""             # the new key is added
    assert merged["uplink"] == "none"
    assert install.merge_config(None, fresh) == fresh


def test_read_config_returns_none_for_absent_or_broken_files():
    r = _repo()
    assert install.read_config(r) is None
    (r / ".solar").mkdir()
    (r / ".solar" / "config.json").write_text("{not json", encoding="utf-8")
    assert install.read_config(r) is None         # a broken config is not a merge source
    shutil.rmtree(r)


# --- the generated ignore block ---------------------------------------------

def test_gitignore_block_is_idempotent_and_updatable():
    """It used to be appended once and never revisable, so each repo hand-argued its own
    policy and they diverged."""
    r = _repo("node_modules/\n")
    assert install.sync_gitignore(r)["action"] == "appended"
    text = (r / ".gitignore").read_text(encoding="utf-8")
    assert "node_modules/" in text and install.BEGIN in text
    assert install.sync_gitignore(r)["action"] == "unchanged"
    # a hand-edited block is REPLACED, never duplicated
    (r / ".gitignore").write_text(
        text.replace(".solar/state/\n", ".solar/state/\n.solar/rogue/\n"), encoding="utf-8")
    assert install.sync_gitignore(r)["action"] == "replaced"
    after = (r / ".gitignore").read_text(encoding="utf-8")
    assert ".solar/rogue/" not in after
    assert after.count(install.BEGIN) == 1
    shutil.rmtree(r)


def test_gitignore_block_appends_to_a_missing_trailing_newline():
    r = _repo("node_modules/")            # no trailing newline
    install.sync_gitignore(r)
    text = (r / ".gitignore").read_text(encoding="utf-8")
    assert text.startswith("node_modules/\n")     # the existing rule is not corrupted
    assert install.BEGIN in text
    shutil.rmtree(r)


def test_rules_outside_the_block_are_reported_not_deleted():
    """Mandarin's real case: a hand-written `.solar/config.json` rule kept the file
    ignored, and the block cannot override it. Report; never rewrite."""
    r = _repo("node_modules/\n.solar/config.json\n.solar/ledger.md\n")
    install.sync_gitignore(r)
    stale = install.stale_solar_rules(r)
    assert [rule for _, rule in stale] == [".solar/config.json", ".solar/ledger.md"]
    assert all(isinstance(n, int) and n > 0 for n, _ in stale)
    # the rules are still on disk, and the block's own rules are NOT reported
    text = (r / ".gitignore").read_text(encoding="utf-8")
    assert ".solar/config.json" in text
    assert ".solar/state/" not in [rule for _, rule in stale]
    shutil.rmtree(r)


def test_a_duplicate_of_a_block_rule_is_not_reported_as_stale():
    """A hand-written `.solar/state/` beside the block changes nothing, and flagging it
    would bury the rules that do matter - Promyro carries four such duplicates."""
    r = _repo(".solar/state/\n.solar/handoffs/\n")
    install.sync_gitignore(r)
    assert install.stale_solar_rules(r) == []
    shutil.rmtree(r)


def test_the_block_tracks_the_record_and_ignores_the_churn():
    r = _repo()
    install.sync_gitignore(r)
    text = (r / ".gitignore").read_text(encoding="utf-8")
    for ignored in (".solar/state/", ".solar/handoffs/", ".solar/chains/",
                    ".solar/objectives/", ".solar/approvals/"):
        assert f"\n{ignored}\n" in text
    # the three files a reviewer needs are deliberately NOT ignored
    for tracked in (".solar/config.json", ".solar/ledger.md", ".solar/runs/"):
        assert f"\n{tracked}\n" not in text
    shutil.rmtree(r)


# --- version marker ----------------------------------------------------------

def test_version_marker_round_trip_and_drift():
    r = _repo()
    assert install.read_version(r) == ""
    status, detail = install.version_status(r)
    assert status == "WARN" and "cannot tell" in detail
    install.write_version(r)
    assert install.read_version(r) == __version__
    assert install.version_status(r)[0] == "PASS"
    install.write_version(r, "5.0.0")
    status, detail = install.version_status(r)
    assert status == "WARN" and "5.0.0" in detail and __version__ in detail
    shutil.rmtree(r)
