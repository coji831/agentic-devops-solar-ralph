"""The write policy against a path that tries to walk out of its own scope.

`write_scope` is an ALLOW list - `repos/pvl-rentals` means "here and nowhere else" - so a path
that satisfies it *falsely* is a bypass rather than a false alarm. `write_deny` is the opposite
direction and fails closed on the same string, which is why the two were able to disagree about
one path for as long as they did.

**Read, reproduced 2026-09-20:** `repos/../records/x.md` kept the raw prefix `repos/`, satisfied
a scope of `["repos"]`, and then `resolve_in_root` collapsed the `..` and wrote `records/x.md` -
outside the scope, inside the repo, reported as `wrote ...`. The cause was that this module
collapsed `.` but never `..`, while the resolver it hands the path to does.

No network and no API key: only the tool layer is exercised.

**Added 2026-09-20, the other half:** `write_glob` is the declared exception that reaches a
SIBLING of the root, where the clones live. Its design rule is the one under test below - **the
escape stays the DEFAULT answer and a glob is an explicit second chance**, so a pattern can add
permission and can never remove any. A guard that raises cannot accidentally allow; a guard that
decides can, so the decision is what the tests are for.

Run:  python -m pytest tests/test_write_policy.py   (or)   python tests/test_write_policy.py
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solar_governor.commands import CommandRunner  # noqa: E402
from solar_governor.workspace import Workspace  # noqa: E402


def _ws(spec: dict) -> Workspace:
    """A workspace over an empty temp root - the policy is what is under test, not the tree."""
    return Workspace(Path(tempfile.mkdtemp(prefix="solar-wp-")), spec)


def _wrote(ws: Workspace, rel: str) -> bool:
    return ws.write_file(rel, "x").startswith("wrote")


SCOPED = {"tools": ["workspace"], "write_scope": ["repos/pvl-rentals"]}
DENIED = {"tools": ["workspace"], "write_deny": ["repos"]}


def test_a_scoped_role_writes_inside_its_scope():
    assert _wrote(_ws(SCOPED), "repos/pvl-rentals/src/x.ts")


def test_dotdot_cannot_satisfy_a_scope():
    """The bypass. `..` collapsed away would leave `records/x.md`, which the scope forbids."""
    ws = _ws(SCOPED)
    assert not _wrote(ws, "repos/../records/x.md")
    assert not _wrote(ws, "repos/sub/../../records/x.md")
    assert not (Path(ws.root) / "records" / "x.md").exists(), "the write must not land at all"


def test_dotdot_cannot_evade_a_deny_either():
    """A deny prefix is matched on the collapsed path too, so walking into it is still denied."""
    ws = _ws(DENIED)
    assert not _wrote(ws, "repos/pvl-rentals/x.ts")
    assert not _wrote(ws, "repos/../repos/pvl-rentals/x.ts")


def test_dotdot_past_the_root_is_denied_by_the_resolver():
    ws = _ws(SCOPED)
    assert not _wrote(ws, "../outside/x.ts")
    assert not _wrote(ws, "repos/../../outside/x.ts")


def test_the_unconditional_layer_is_still_matched_on_raw_segments():
    """Conservative on purpose: agent config is denied even when the path would collapse clear.

    `.solar/../records/x.md` resolves to `records/x.md`, which nothing protects - but the
    unconditional layer sees `.solar` in the path and refuses. That is the safe direction, and it
    is deliberately NOT the behaviour the role layer uses.
    """
    assert not _wrote(_ws(SCOPED), ".solar/../records/x.md")
    assert not _wrote(_ws(SCOPED), ".github/x.md")


def test_a_role_with_no_scope_writes_anywhere_but_the_deny_list():
    """`recorder` and `proposer` are unscoped, so the deny list is all that confines them."""
    ws = _ws({"tools": ["workspace"]})
    assert _wrote(ws, "records/x.md")
    assert _wrote(ws, "docs/x.md")
    assert not _wrote(ws, "package.json")


# --- write_glob: the declared exception that reaches a SIBLING -------------------------------
#
# The clones are siblings of the runtime root, so `resolve_in_root` refuses every write to one
# BEFORE any policy is consulted. `write_glob` is the explicit exception, specified in
# `Promyro/context/runner/06-write-scope-patterns.md` on 2026-09-20.

GLOB = {"tools": ["workspace"], "write_scope": ["repos"],
        "write_glob": ["../repos/solar-sandbox/**"]}
UNANCHORED = {"tools": ["workspace"], "write_scope": ["repos"],
              "write_glob": ["../*/**"]}


def _sibling_ws(spec: dict) -> Workspace:
    """A workspace whose root has a real `repos/` SIBLING - the layout a glob exists for.

    Self-contained: root and sibling share one throwaway parent, so a test never writes into
    the system temp root itself.
    """
    parent = Path(tempfile.mkdtemp(prefix="solar-glob-"))
    root = parent / "Promyro"
    root.mkdir(parents=True, exist_ok=True)
    return Workspace(root, spec)


def test_glob_lets_a_sibling_be_written():
    """1 - the unlock itself: a write OUTSIDE the root, which nothing else can reach."""
    assert _wrote(_sibling_ws(GLOB), "../repos/solar-sandbox/src/x.ts")


def test_the_glob_is_not_a_blanket():
    """2 - one pattern, one client. A sibling it does not name stays out of reach."""
    ws = _sibling_ws(GLOB)
    assert not _wrote(ws, "../repos/other-client/src/x.ts")
    assert not (Path(ws.root).parent / "repos" / "other-client").exists()


def test_collapse_runs_before_the_glob_match():
    """3 - the `..` bypass in its new form: arriving at the clone obliquely must not count."""
    assert not _wrote(_sibling_ws(GLOB), "../repos/solar-sandbox/../../other-client/x.ts")


def test_the_deny_layers_outrank_the_glob():
    """4 - an allow is not an amnesty: config, metadata and the lock still refuse."""
    ws = _sibling_ws(GLOB)
    assert not _wrote(ws, "../repos/solar-sandbox/package.json")
    assert not _wrote(ws, "../repos/solar-sandbox/.git/config")
    assert not _wrote(ws, "../repos/solar-sandbox/.solar/state/LOCK")


def test_an_uncovered_escape_is_still_refused():
    """5 - the default is unchanged: outside the root and outside the globs means no."""
    ws = _sibling_ws(GLOB)
    assert not _wrote(ws, "../outside/x.ts")
    assert not (Path(ws.root).parent / "outside").exists()


def test_a_glob_does_not_unlock_a_commands_cwd():
    """6 - the grant belongs to the WRITE layer. A command's `cwd` keeps the old resolver.

    Lifting `resolve_in_root` itself would hand the shell what the write layer granted to a
    file, so the write layer got a second resolver instead of a weakened first one.
    """
    parent = Path(tempfile.mkdtemp(prefix="solar-glob-"))
    runner = CommandRunner(parent / "Promyro",
                           {"tools": ["exec"], "write_glob": ["../repos/solar-sandbox/**"]},
                           vocabulary={}, human_approval=False)
    try:
        runner._cwd({"cwd": "../repos/solar-sandbox"})
    except ValueError:
        pass
    else:  # pragma: no cover - reached only on the failure this test exists to catch
        raise AssertionError("a command's cwd escaped the repo root")


def test_an_absent_or_empty_glob_changes_nothing():
    """7 - the regression guard for every registry written before today."""
    for empty in ({}, {"write_glob": []}, {"write_glob": None}, {"write_glob": ""}):
        ws = _sibling_ws({**SCOPED, **empty})
        assert not _wrote(ws, "../repos/solar-sandbox/src/x.ts"), empty


def test_an_unanchored_pattern_is_refused_rather_than_obeyed():
    """`../*/**` reads like a pattern and behaves like a blanket: `fnmatch`'s `*` crosses `/`.

    It grants nothing, and the refusal is still NAMED in the reason - a pattern that fails
    silently is a typo nobody ever finds.
    """
    ws = _sibling_ws(UNANCHORED)
    assert not _wrote(ws, "../Windows/System32/x.dll")
    assert not _wrote(ws, "../repos/solar-sandbox/src/x.ts")
    assert "unanchored" in ws.write_file("../repos/solar-sandbox/src/x.ts", "x")
