"""T53: a role's brief is agnostic, and the DECLARED clone's own facts are loaded beside it.

The gap this closes was measured: `clone` appeared in NO prompt or message construction
anywhere in the package, because `_role_prompt(spec, role)` could see only the spec and the
role name. The run declared its clone (`T50`), the card recorded it, the command layer
resolved `cwd` from it - and a brief still could not learn which repository it was in. So
there was nowhere for a per-repo fact to live except the brief itself, and it landed in two
texts that drifted in 20 of 21 repo-identity tokens.

These tests are that chain, end to end: a file on disk, the clone in the graph state, and the
prompt a link is actually dispatched with.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solar_governor import executor, graph              # noqa: E402
from solar_governor.core import Config                  # noqa: E402

REGISTRY = {
    "reviewer": {"role": "Reviewer", "system": "You review.", "tools": [],
                 "next_edges": [], "model": "", "write": False},
}
CONVENTIONS = ("# pvl-rentals\n\n"
               "i18n keys go in BOTH `de.json` and `en.json`. `Decimal(12,2)`, never a float.\n")


def _repo() -> Path:
    r = Path(tempfile.mkdtemp(prefix="t53-test-"))
    (r / ".solar").mkdir(parents=True)
    (r / ".solar" / "registry.json").write_text(json.dumps(REGISTRY, indent=2), encoding="utf-8")
    return r


def _with_conventions(r: Path, clone: str, text: str = CONVENTIONS) -> Path:
    d = r / ".github" / "skills" / "repo-conventions"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{clone}.md").write_text(text, encoding="utf-8", newline="\n")
    return d


def test_no_clone_declared_returns_the_brief_UNCHANGED():
    """Equality, not a substring - so `clone=""` cannot pass by appending nothing visible."""
    r = _repo()
    try:
        cfg = Config(repo=str(r), runner="stub")
        got = graph._role_prompt(cfg, REGISTRY["reviewer"], "reviewer", "")
        assert got == "You review.", got
    finally:
        shutil.rmtree(r, ignore_errors=True)


def test_a_clone_with_no_file_is_the_ordinary_case():
    """A repository with nothing unusual needs no file, and that is not an error."""
    r = _repo()
    try:
        cfg = Config(repo=str(r), runner="stub")
        got = graph._role_prompt(cfg, REGISTRY["reviewer"], "reviewer", "solar-sandbox")
        assert got == "You review.", got
    finally:
        shutil.rmtree(r, ignore_errors=True)


def test_the_clones_own_file_is_appended_and_theSOURCE_is_named():
    """The source is named in the prompt on purpose - see the loader's docstring.

    A typo'd directory must not read like a clone that has no conventions, so the reader is
    told "loaded, from here" rather than being asked to trust a path.
    """
    r = _repo()
    try:
        _with_conventions(r, "pvl-rentals")
        cfg = Config(repo=str(r), runner="stub")
        got = graph._role_prompt(cfg, REGISTRY["reviewer"], "reviewer", "pvl-rentals")
        assert got.startswith("You review."), got
        assert "de.json" in got, "the clone's facts did not reach the prompt"
        assert ".github/skills/repo-conventions/pvl-rentals.md" in got, got
        assert "--clone pvl-rentals" in got, got
    finally:
        shutil.rmtree(r, ignore_errors=True)


def test_another_clones_facts_do_NOT_leak_in():
    """The whole point: a link is told about the repository it is in and about no other."""
    r = _repo()
    try:
        _with_conventions(r, "pvl-rentals")
        _with_conventions(r, "solar-sandbox", "# solar-sandbox\n\nUse `node --test`.\n")
        cfg = Config(repo=str(r), runner="stub")
        got = graph._role_prompt(cfg, REGISTRY["reviewer"], "reviewer", "solar-sandbox")
        assert "node --test" in got, got
        assert "de.json" not in got, "pvl-rentals' conventions leaked into another clone's prompt"
    finally:
        shutil.rmtree(r, ignore_errors=True)


def test_a_name_that_is_not_a_plain_directory_name_loads_nothing():
    """`clone` is refused at the START of a run, so this is a second belt - but this function
    builds a path the first one never saw, so it must not interpolate an escape."""
    r = _repo()
    try:
        cfg = Config(repo=str(r), runner="stub")
        for bad in ("../repos/pvl-rentals", "..", ".", "none", "", "a/b", "a\\b", "C:\\Windows"):
            assert graph.clone_conventions(cfg, bad) == ("", ""), bad
            assert graph._role_prompt(cfg, REGISTRY["reviewer"], "reviewer", bad) == "You review."
    finally:
        shutil.rmtree(r, ignore_errors=True)


def test_the_declared_clone_reaches_the_prompt_through_the_GRAPH():
    """**The test the gap needed.** Everything above proves the loader; this proves the chain.

    The clone rides the graph state, so this fails if either call site stops passing it - which
    is the half that did not exist before `T53`.
    """
    r = _repo()
    try:
        _with_conventions(r, "pvl-rentals")
        cfg = Config(repo=str(r), runner="stub")
        seen: dict = {}
        orig = executor.run

        def _capture(**kw):
            seen.update(kw)
            return {"output": "ok"}

        executor.run = _capture
        try:
            graph._execute(cfg, {"role": "reviewer", "objective": "audit the change",
                                 "clone": "pvl-rentals"})
        finally:
            executor.run = orig

        prompt = seen.get("system_prompt", "")
        assert prompt.startswith("You review."), prompt
        assert "de.json" in prompt, (
            "the declared clone did not reach the prompt - `_execute` stopped passing `state['clone']`"
        )
        assert seen.get("clone") == "pvl-rentals"
    finally:
        shutil.rmtree(r, ignore_errors=True)


def test_the_HANDOFF_names_the_same_source():
    """The other call site. A handoff embeds the prompt in a fenced block, so a clone's facts
    must be in what the human's agent is handed - not only in what an HTTP runner receives.

    `interrupt` is caught broadly and deliberately: it is the NEXT statement, it needs a real
    graph run to work, and the handoff has already been built by the time it is reached.
    """
    r = _repo()
    try:
        _with_conventions(r, "pvl-rentals")
        cfg = Config(repo=str(r), runner="agent-dispatch")
        captured: dict = {}
        orig = executor.write_handoff

        def _capture_handoff(**kw):
            captured.update(kw)
            return r / "handoff.md"

        executor.write_handoff = _capture_handoff
        try:
            graph._dispatch_agent(cfg, {"role": "reviewer", "objective": "audit",
                                        "clone": "pvl-rentals", "chain": ""}, 1)
        except Exception:
            pass                                    # `interrupt`, after the handoff exists
        finally:
            executor.write_handoff = orig

        assert "de.json" in captured.get("system_prompt", ""), (
            "the handoff path stopped loading the declared clone's conventions"
        )
    finally:
        shutil.rmtree(r, ignore_errors=True)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok  {name}")
    print("all role-conventions tests passed")
