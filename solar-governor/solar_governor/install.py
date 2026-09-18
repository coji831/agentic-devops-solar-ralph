"""Install surface: what `init` writes into a repo, and how it stays in one piece.

Two problems this module exists to solve, both found by comparing two real
engagements against each other (2026-09-19):

* **Re-running `init` was destructive and asymmetric.** It overwrote `config.json`
  unconditionally - losing a model pin - while writing `registry.json` only if
  absent. So nobody re-ran it, and every install drifted from the runtime.
* **The `.gitignore` policy was hand-argued per repo.** `init` appended a list once
  and could never revise it (its guard was `if ".solar/state" not in text`, which
  silently skipped the whole block if anything else had already written that string).
  The two engagements ended up with *opposite* rules for `.solar/config.json`; the one
  that ignored it is the one where a non-existent model id sat unreviewed.

The block below is marker-delimited, so re-running `init` REPLACES it. Rules a repo
wrote by hand outside the block are reported, never rewritten: they still apply, the
block cannot override them, and silently deleting someone's rules is worse than a
warning.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import __version__
from .core import read_json, read_text

BEGIN = "# >>> solar-governor — generated block; rewritten by `solar-governor init` >>>"
END = "# <<< solar-governor <<<"
VERSION_FILE = ".solar/VERSION"

# Ignored    = churn, not history.
# Tracked    = the record. Anything a future reader would need in order to know what
#              happened, or to review a decision, belongs in version control.
GITIGNORE_BODY = """\
# Rewritten by `solar-governor init`. Edit OUTSIDE these markers if you must; anything
# added inside is lost on the next init.
#
# IGNORED — churn, not history:
#   .solar/state/       SQLite checkpoints, rewritten every graph step
#   .solar/handoffs/    one file per agent-dispatch link, superseded on resume
#   .solar/chains/      per-link chain scratch
#   .solar/objectives/  the text of what one link was asked to do
#   .solar/approvals/   pending and decided approval requests for one command
#
# TRACKED ON PURPOSE — this is the record:
#   .solar/ledger.md      the running record: one section per run, appended to and never
#                         rewritten, so hand-written content in this file is safe
#   .solar/runs/          one run-card per dispatch: the structured record, with decisions
#   .solar/config.json    portable since v5.6.0 (no absolute paths), so it is
#                         reviewable - a stale model pin has to show up in a diff
#   .solar/registry.json  roles, grants and prompts
#   .solar/commands.json  the vetted command vocabulary
#   .solar/VERSION        which runtime version this repo was installed against
.solar/state/
.solar/handoffs/
.solar/chains/
.solar/objectives/
.solar/approvals/
"""


def block() -> str:
    """The generated `.gitignore` block, markers included, with NO trailing newline.

    The caller supplies the newline. A block that carried its own would gain one more
    on every rebuild, so `sync_gitignore` could never report "unchanged" - the
    idempotence test caught exactly that.
    """
    return f"{BEGIN}\n{GITIGNORE_BODY}{END}"


def block_patterns() -> set[str]:
    """The patterns the generated block itself declares."""
    return {line.strip() for line in GITIGNORE_BODY.splitlines()
            if line.strip().startswith((".solar/", "!.solar/"))}


def stale_solar_rules(root: Path) -> list[tuple[int, str]]:
    """`(line number, rule)` for `.solar/...` rules **outside** the generated block
    that the block does NOT already cover.

    Duplicates are not reported: a hand-written `.solar/state/` beside the block changes
    nothing, and flagging it would bury the rules that DO matter. What matters is a rule
    the block disagrees with - an ignored `.solar/config.json` keeps the file out of
    review however the block is written, and that is how a non-existent model id sat
    unseen. Reported with real line numbers, and never rewritten: silently deleting
    someone's rules is worse than a warning.
    """
    path = Path(root) / ".gitignore"
    if not path.is_file():
        return []
    covered = block_patterns()
    out: list[tuple[int, str]] = []
    inside = False
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if stripped == BEGIN:
            inside = True
            continue
        if stripped == END:
            inside = False
            continue
        if inside or stripped in covered:
            continue
        if stripped.startswith((".solar/", "!.solar/")):
            out.append((i, stripped))
    return out


def sync_gitignore(root: Path) -> dict:
    """Write (or rewrite) the generated block. Returns what it did.

    Idempotent: a repo already carrying the current block is left byte-identical.
    """
    path = Path(root) / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    fresh = block()
    if BEGIN in text and END in text:
        head, rest = text.split(BEGIN, 1)
        _, tail = rest.split(END, 1)          # tail keeps the original trailing newline
        updated = head + fresh + tail
        action = "replaced" if updated != text else "unchanged"
    else:
        prefix = text
        if prefix and not prefix.endswith("\n"):
            prefix += "\n"
        if prefix:
            prefix += "\n"
        updated = prefix + fresh + "\n"
        action = "appended"
    if updated != text:
        path.write_text(updated, encoding="utf-8")
    return {"action": action, "path": str(path), "stale": stale_solar_rules(root)}


def merge_config(existing: dict | None, fresh: dict) -> dict:
    """Keep every setting already present; add the ones a new version introduces.

    Existing wins. A repo may have tuned `model`, `runner` or `human_approval`, and
    init's job is to add keys - not to reset the repo to shipped defaults. This is the
    difference between a re-install being a decision and being a gamble.
    """
    if not existing:
        return dict(fresh)
    merged = dict(fresh)
    merged.update(existing)
    return merged


def read_version(root: Path) -> str:
    """The runtime version this repo was installed against ("" when unrecorded).

    BOM-tolerant: a marker carrying one would otherwise compare as
    `\ufeff5.6.2` and report drift that does not exist.
    """
    path = Path(root) / VERSION_FILE
    if not path.is_file():
        return ""
    try:
        return read_text(path).strip()
    except OSError:
        return ""


def write_version(root: Path, version: str = __version__) -> Path:
    path = Path(root) / VERSION_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{version.strip()}\n", encoding="utf-8")
    return path


def version_status(root: Path) -> tuple[str, str]:
    """(status, detail) for `doctor` - a repo that has drifted from the runtime.

    Not a FAIL: an older marker is a fact about when the repo was installed, and the
    runtime is backwards compatible within a line. It is a WARN because drift is
    exactly what nobody notices until something behaves like an older version.
    """
    installed = read_version(root)
    if not installed:
        return "WARN", (f"no {VERSION_FILE} — cannot tell which runtime this repo was "
                        f"installed against (runtime is {__version__})")
    if installed != __version__:
        return "WARN", (f"installed against {installed}, runtime is {__version__} — "
                        f"re-run `solar-governor init` to refresh")
    return "PASS", f"installed against {installed} (runtime {__version__})"


def read_config(root: Path) -> dict | None:
    """The raw config dict on disk, or None. Used for the merge, before dataclass
    filtering, so an unknown key a future version wrote is not silently dropped."""
    path = Path(root) / ".solar" / "config.json"
    if not path.is_file():
        return None
    try:
        data = read_json(path)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None
