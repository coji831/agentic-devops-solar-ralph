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

Run:  python -m pytest tests/test_write_policy.py   (or)   python tests/test_write_policy.py
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
