"""Workspace tool layer (v5 tool layer, light subset): repo-bounded read/glob/
write helpers exposed to the model executor as function tools.

Sovereignty guard (v5 §11): every path is resolved and confined to the repo
root; writes refuse paths that escape it. No shell/exec here (light profile).
"""
from __future__ import annotations

import copy
import fnmatch
import os
import re
from pathlib import Path

# dirs never surfaced / written, even inside the repo
_SKIP_DIRS = {".git", "node_modules", ".solar", ".next", "dist", "build",
              "__pycache__", ".venv", "venv", "coverage", ".terraform", ".cache"}
_SKIP_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff",
              ".woff2", ".ttf", ".eot", ".map", ".sqlite", ".db", ".lock"}
MAX_READ_CHARS = 40_000

# The budget ONE search result keeps, and it is deliberately under `SOLAR_TOOL_OUTPUT_CHARS`'s
# 8000 default (`executor.tool_output_chars`). That cap cuts a result's TAIL and appends its own
# marker - which on a search means the "narrow it" advice is the first thing lost, and the model is
# left holding a hit list that looks complete. A budget the tool applies itself can name the limit
# it hit and what to do instead, so the elision stays a fact the model can report (T34, 2026-09-23).
SEARCH_MAX_CHARS = 6_000

# A SEARCH hit is a POINTER, not a reading - its job is to be citable and to make the NEXT call
# cheap. `MAX_LINE_CHARS` is the right budget for `read_file`, where a long line is a legitimate
# answer, and the wrong one here: measured 2026-09-23, two wide table rows in one instruction file
# spent the whole result budget on two hits and cut the walk at 17 of 187 files. 400 chars is
# enough to recognise the line, and `read_file(rel, n, n)` returns it in full.
SEARCH_MAX_LINE_CHARS = 400

# A line is NOT a size bound (TD-5.7-5). `read_file(rel, 1, 60)` on a file whose only line was
# 282,604 chars - a `.tsbuildinfo`, minified JS, a lockfile, a one-line data blob - returned
# 282,669 chars: about 70k tokens against a window a local model has 16k of, and it then stays
# in history for the rest of the run. One line is capped at the size this runtime already gives
# one COMMAND's output (`commands.DEFAULT_MAX_OUTPUT`), and the marker names the line and its
# real length, so the elision is a fact the model can report rather than a silent gap.
MAX_LINE_CHARS = 4_000


def _clip_line(text: str, lineno: int, cap: int = MAX_LINE_CHARS) -> str:
    """One line of a file, bounded, with the elision spelling itself out (see MAX_LINE_CHARS).

    `cap` is a parameter because the two callers want different budgets and both are right:
    `read_file` returns a READING, where one long line is a legitimate answer, and `search_text`
    returns a POINTER, where it is not (T34, 2026-09-23).
    """
    if len(text) <= cap:
        return text
    return (f"{text[:cap]}…[line {lineno} elided: {len(text)} chars, first {cap} shown]")


def _numbered(lines: list[str], lo: int, hi: int, total: int) -> str:
    """The selected lines, each prefixed with its 1-based number and a pipe.

    **Added 2026-09-20, because its absence made a role's contract unkeepable.** This tool is
    the `http` runner's ONLY way to read a file, and it returned bare text: a model could quote
    a line but not cite one, so `investigator`'s `path:line` contract had no implementable form
    on that runner - and the whole point of moving links to `http` is that they carry the
    numbers. `read_file` already received every line's number for its elision marker; this
    passes the same number through to the reader.

    The number is padded to the FILE's width rather than the selection's, so a citation reads
    the same across two reads of one file.
    """
    if not lines or hi < lo:
        return ""
    pad = len(str(total))
    return "\n".join(f"{n:>{pad}}| {_clip_line(lines[n - 1], n)}" for n in range(lo, hi + 1))

# Write deny-list (v5.4.0). Agent configuration and execution-defining files:
# rewriting one of these lets an injected prompt change the agent's own
# instructions, its tool policy, or the repo's CI behaviour — with no shell
# needed. Unconditional, and a mechanical restatement of rules the role prompts
# already state in prose. Matched case-insensitively (Windows/macOS filesystems
# are) on any path segment at any depth, not just at the repo root.
_WRITE_DENY_DIRS = {".solar", ".git", ".github", ".vscode"}
_WRITE_DENY_NAMES = {".mcp.json", "package.json", "package-lock.json",
                     "pyproject.toml", "requirements.txt", "dockerfile",
                     "docker-compose.yml", "makefile"}

# The READ side of the sibling grant (C2, 2026-09-20). **The same two lists, imported rather than
# restated** - a second copy of a deny list is a second thing to keep in sync, and rule 4 of the
# engagement's decoupling rules says a set has one home.
_READ_DENY_DIRS = _WRITE_DENY_DIRS
_READ_DENY_NAMES = _WRITE_DENY_NAMES


def _read_denial(rel: str) -> str | None:
    """Why `rel` may not be READ through a glob, or None. **Only consulted OUTSIDE the root.**

    **The deny NAMES cost something here that they do not cost on the write side, and that is not
    obvious.** On a write, `package.json` is protected because a role editing it changes what the
    project resolves. On a READ the same name is the most useful file in a JavaScript repository -
    so reusing the list is a real restriction on the feature's usefulness, and it is stated here
    rather than discovered later: **an `http` implementer cannot read the clone's `package.json`,
    `pyproject.toml` or lockfiles.** The DIRECTORIES are the part that pays for itself, because
    `.git/config` can carry a credential inside a remote URL.

    **`.env` is added here, and it was in NEITHER write list** - so "reuse the deny list" leaked it.
    A read deny list whose stated purpose is keeping secrets out of the payload, that omits the one
    file secrets are conventionally written in, is not a scope choice; it is the defect the list
    exists to prevent. `.env.local` and friends are matched by prefix, because a suffix rule would
    miss the files people actually use.
    """
    raw = [p for p in rel.replace("\\", "/").split("/") if p not in ("", ".")]
    for part in raw[:-1]:
        if part.lower() in _READ_DENY_DIRS:
            return f"{part}/ is protected (agent config / repo metadata)"
    name = (raw[-1] if raw else "").lower()
    if name in _READ_DENY_NAMES:
        return f"{name} is protected (defines tooling, deps or CI)"
    if name == ".env" or name.startswith(".env."):
        return f"{name} is protected (credentials)"
    return None


def _collapse(segments: list[str]) -> list[str]:
    """Collapse `.` and `..` the way `Path.resolve()` does, so policy sees the real path.

    **Read, reproduced 2026-09-20.** The write policy matched its RAW segments, dropping only
    `""` and `"."`, so `repos/../records/x.md` kept the prefix `repos/`, satisfied a
    `write_scope` of `["repos"]`, and then `resolve_in_root` collapsed the `..` and wrote
    `records/x.md`. **A scope is an ALLOW list, so matching it wrongly is a bypass rather than a
    false alarm** - while `write_deny` on the same string happened to fail closed, by luck of
    direction. Two layers that decide the same write must see the same path; this is how.

    A `..` that would climb past the start is KEPT rather than dropped: escaping the root is not
    this function's call to make, and leaving it in makes the prefix match fail, which is the
    safe direction.
    """
    out: list[str] = []
    for part in segments:
        if part in ("", "."):
            continue
        if part == "..":
            if out and out[-1] != "..":
                out.pop()
            else:
                out.append(part)
            continue
        out.append(part)
    return out


def _norm_prefixes(value) -> list[str]:
    """Normalise a registry prefix list to repo-relative, forward-slashed form."""
    if isinstance(value, str):
        value = [value]
    if not value:
        return []
    return [str(v).replace("\\", "/").strip("/") for v in value if str(v).strip("/")]


_WILDCARDS = ("*", "?", "[")


def _norm_rel(rel: str) -> str:
    """The path the POLICY decides on: repo-relative, forward-slashed, and COLLAPSED.

    One function, so that two layers judging the same write cannot be shown two different
    paths - which is precisely what produced the `..` bypass. A leading `..` survives here:
    escaping the root is the caller's call to make, and this one only normalises.
    """
    raw = [p for p in str(rel).replace("\\", "/").split("/") if p not in ("", ".")]
    return "/".join(_collapse(raw))


def _glob_parts(value) -> tuple[list[str], list[str]]:
    """Split a registry `write_glob` into (anchored patterns, refused patterns).

    A pattern is REFUSED rather than repaired when its first segment after the leading `..`
    run is a wildcard. `../*/**` reads like a pattern and behaves like a blanket, because
    `fnmatch`'s `*` crosses `/` (unlike `glob`'s) - and the unconditional deny list has no
    rule for `../Windows/System32`. One rule instead, and it is checkable by eye: **a
    pattern must name a literal directory before any wildcard.**

    A refused pattern is returned rather than dropped, so the refusal can name it; dropping
    it silently would turn a typo into a mystery.
    """
    if isinstance(value, str):
        value = [value]
    if not value:
        return [], []
    good: list[str] = []
    bad: list[str] = []
    for v in value:
        pat = _norm_rel(v)
        parts = [p for p in pat.split("/") if p]
        first_wild = next((i for i, p in enumerate(parts)
                           if any(c in p for c in _WILDCARDS)), None)
        if first_wild is not None and all(p == ".." for p in parts[:first_wild]):
            bad.append(pat)
            continue
        good.append(pat)
    return good, bad


def _glob_covers(norm: str, patterns: list[str]) -> bool:
    """Whether an anchored pattern covers the collapsed, repo-relative path.

    Case-SENSITIVE on every platform (`fnmatchcase`, not `fnmatch`): a policy that answers
    differently on Windows than on Linux is not a policy, and a path differing only in case
    then fails closed, which is the direction a grant should fail.

    **A pattern ending `/**` also covers the directory itself** - added 2026-09-20 with C2, and it
    is not a convenience. `X/**` is the ordinary spelling for "everything under X", and without this
    clause it covered `X/src/a.js` and NOT `X`: a role could read every file in a sibling and could
    not LIST it, because `list_tree` addresses the directory. **That is the write-only grant's
    failure one layer up** - the grant works, the traversal does not, and the role cannot find what
    it is allowed to touch. `**` means "inside", and finding what is inside starts by addressing it.
    """
    for pat in patterns:
        if fnmatch.fnmatchcase(norm, pat):
            return True
        if pat.endswith("/**") and norm == pat[:-3].rstrip("/"):
            return True
    return False


def resolve_in_root(root: Path, rel: str) -> Path:
    """Resolve a repo-relative path and enforce confinement to the repo root.

    Shared by the workspace layer and the command layer: a command's `cwd` has to be
    inside the repo for the same reason a write does.
    """
    root = Path(root).expanduser().resolve()
    p = (root / rel).resolve()
    if p != root and root not in p.parents:
        raise ValueError(f"path escapes repo root: {rel!r}")
    return p


class Workspace:
    """Repo-bounded file access for one governor run.

    `spec` is the ROLE's registry entry (v5 §6), passed in by the executor so
    policy can be derived from the role rather than the process: which tools the
    role is OFFERED (`tools`, `write`) and where it may write (`write_deny`,
    `write_scope`). Deep-copied so a caller's registry dict is never mutated.

    Registry contract (all optional; absent means unchanged historical behaviour):

        tools        ["workspace", "exec"]  tool GROUPS (absent/[] = "workspace")
        write        false                 the role is read-only: `write_file` is
                                           neither offered nor permitted
        write_deny   ["emails"]            extra path prefixes this role may not write
        write_scope  ["repos/pvl-rentals"] if set, writes MUST fall under one of these
        write_glob   ["../repos/x/**"]     anchored globs over the COLLAPSED repo-relative
                                           path: the only way a write may reach a SIBLING
                                           of the root. Checked last, after every deny,
                                           and it can only add permission.
    """

    def __init__(self, root: Path, spec: dict | None = None):
        self.root = Path(root).expanduser().resolve()
        self.spec = copy.deepcopy(spec) if spec else {}

    # --- guards -----------------------------------------------------------
    def _resolve(self, rel: str) -> Path:
        """Resolve a repo-relative path and enforce confinement to root."""
        return resolve_in_root(self.root, rel)

    def _resolve_for_write(self, rel: str) -> tuple[Path, bool]:
        """Resolve `rel` for the WRITE layer, and say whether it stayed inside the root.

        The write layer cannot start at `resolve_in_root`, and that is not a weakening of
        it: a `write_glob` can only be matched against a path that has ALREADY been
        resolved, and the write a glob exists to permit is exactly the one that escapes.

        **So the refusal moves rather than disappears.** `write_file` still refuses every
        path that is outside the root and outside the globs, so the escape remains the
        DEFAULT answer and a glob is an explicit second chance - the shape matters more
        than the check, because a guard that raises cannot accidentally allow.

        The command layer keeps the original resolver untouched: a `cwd` is not a write,
        and the vocabulary's argv already reaches a clone legitimately.
        """
        root = self.root
        p = (root / str(rel)).resolve()
        return p, (p == root or root in p.parents)

    def _glob_allows(self, rel: str) -> bool:
        """Whether this role's anchored `write_glob` covers `rel` - its sibling reach."""
        globs, _ = _glob_parts(self.spec.get("write_glob"))
        return _glob_covers(_norm_rel(rel), globs)

    def _glob_roots(self) -> list[tuple[Path, str]]:
        """The directories this role's globs literally name: `(resolved dir, prefix as written)`.

        Derived from the pattern rather than declared beside it, so there is one home for the
        grant. `../repos/solar-sandbox/**` gives `(C:/CodeProjects/Freelance/repos/solar-sandbox,
        '../repos/solar-sandbox/')`. The prefix keeps the `../` because that is how the model has
        to write the path - the tools speak repo-relative, and a sibling is only addressable from
        outside.
        """
        roots: list[tuple[Path, str]] = []
        for pat in _glob_parts(self.spec.get("write_glob"))[0]:
            parts = [p for p in pat.split("/") if p]
            cut = next((i for i, p in enumerate(parts) if any(c in p for c in "*?[")), len(parts))
            literal = "/".join(parts[:cut])
            if not literal:
                continue
            base = (self.root / literal).resolve()
            if base.is_dir():
                roots.append((base, literal.rstrip("/") + "/"))
        return roots

    def _resolve_for_read(self, rel: str) -> Path:
        """Resolve `rel` for a READ, admitting a glob-covered sibling (C2, 2026-09-20).

        **The escape is still the default answer.** `resolve_in_root` runs first, and a path
        outside the root raises exactly as it did - unless the role's anchored `write_glob` covers
        it AND the path survives the read deny list. So this is the write grant's rule pointed the
        other way, with the same two properties: the glob can only ADD permission, and it is
        matched against the COLLAPSED path so `../repos/x/../../etc/passwd` cannot arrive obliquely.

        **One key governs both layers, deliberately, and the measurement is why.** A role that may
        write in a tree it cannot read cannot list it, cannot match the style of the files it was
        told to change, and cannot read back what it wrote. Measured 2026-09-20 in the Promyro
        engagement: the write grant worked, the agent refused to use it, and said in its own report
        that a write it knows will be rejected *"is not a test of anything"*. The two halves are one
        capability.

        **The read deny list applies ONLY to a glob-covered path.** Inside the root, reads are
        exactly what they were - those lists exist because a sibling is somebody else's tree, and
        applying them to our own would be a restriction nobody asked for.
        """
        try:
            return resolve_in_root(self.root, rel)
        except ValueError:
            if not self._glob_allows(rel):
                raise                        # unchanged: no glob covers it, so it escapes
            denial = _read_denial(rel)
            if denial:
                raise ValueError(f"refusing to read {rel}: {denial}")
            return (self.root / str(rel)).resolve()

    def _write_denial(self, rel: str) -> str | None:
        """Why `rel` may not be written, or None when it may.

        Two layers. The first is UNCONDITIONAL — agent config and
        execution-defining files, matched on any segment at any depth; it does
        not consult the role, the objective, or anything the model influences.
        The second is per-ROLE, from the registry spec: extra denied prefixes
        and, when `write_scope` is set, confinement to an allowed subtree.
        Neither is a suggestion.
        """
        # The UNCONDITIONAL layer stays matched on the RAW segments, deliberately: it protects
        # specific files and directories, a false alarm there costs a retry, and a miss costs the
        # agent's own config. Only the ROLE layer takes the collapsed path - a scope decides what
        # is ALLOWED, so matching it against the wrong path is the bypass closed on 2026-09-20.
        raw = [p for p in rel.replace("\\", "/").split("/") if p not in ("", ".")]
        for part in raw[:-1]:
            if part.lower() in _WRITE_DENY_DIRS:
                return f"{part}/ is protected (agent config / repo metadata)"
        name = raw[-1] if raw else ""
        if name.lower() in _WRITE_DENY_NAMES:
            return f"{name} is protected (defines tooling, deps or CI)"
        return self._role_write_denial("/".join(_collapse(raw)))

    def _role_write_denial(self, norm: str) -> str | None:
        """The per-role half of the write policy: denied prefixes, then scope, then globs.

        `write_scope` is a prefix list over paths INSIDE the root; `write_glob` is the
        explicit exception that reaches a sibling. The glob is consulted LAST and only when
        the scope would refuse, so it can add permission and can never remove any.
        """
        for prefix in _norm_prefixes(self.spec.get("write_deny")):
            if norm == prefix or norm.startswith(prefix + "/"):
                return f"{prefix}/ is denied for this role"
        scope = _norm_prefixes(self.spec.get("write_scope"))
        globs, refused = _glob_parts(self.spec.get("write_glob"))
        if scope and not any(norm == a or norm.startswith(a + "/") for a in scope):
            if _glob_covers(norm, globs):
                return None
            hint = (f" (write_glob refused as unanchored: {', '.join(refused)})"
                    if refused else "")
            return ("outside this role's write scope "
                    f"({', '.join(a + '/' for a in scope)}){hint}")
        return None

    def verdict(self, rel: str) -> str:
        """Why a write to `rel` would be refused, or `"allowed"`.

        **The READER of the policy, and the reason it cannot disagree with the enforcement is
        that it IS the enforcement:** `_write_denial` computes this on every attempt and throws
        the string away, so a role learns its boundary one refusal at a time - and a role told to
        write where it knows it will be refused reports that a test it cannot pass *"is not a
        test of anything"* (measured 2026-09-20, recorded in `_resolve_for_read` above).
        """
        return self._write_denial(rel) or "allowed"

    def policy(self, role: str = "") -> dict:
        """The whole write policy as data, rather than as a refusal.

        Answers *"may I write here?"* **before** the attempt, which is the one question this
        engagement could not ask: `agent-tool-surface.md` section 4 measured it and the shape is
        the finding - **42 checks that can say afterwards that something was wrong, and nothing
        that says beforehand what is allowed.**

        Four layers decide a write and only two of them are the role's: its `write_deny`, and
        its `write_scope` with `write_glob` as the single exception that reaches a sibling. The
        other two are unconditional and hold whatever the role says.

        `role` is the registry KEY when the caller knows it, because the spec's own `role` field
        is a display name (`"Recorder"`) and the key is the identity every other record uses. The
        resolved `root` is reported because it is the directory a relative path resolves
        against - the one thing the IDE path cannot answer for itself.
        """
        scope = _norm_prefixes(self.spec.get("write_scope"))
        globs, refused = _glob_parts(self.spec.get("write_glob"))
        may = self.allows_write()
        return {
            "role": role or str(self.spec.get("role") or ""),
            "root": str(self.root),
            "may_write": may,
            "write_scope": scope,
            "write_glob": globs,
            "write_glob_refused": refused,
            "write_deny": _norm_prefixes(self.spec.get("write_deny")),
            "protected_dirs": sorted(_WRITE_DENY_DIRS),
            "protected_names": sorted(_WRITE_DENY_NAMES),
            "allowed_prefixes": [f"{a}/" for a in scope] if scope else (
                ["<anywhere the protected names and dirs do not cover>"] if may else []),
        }

    # --- role capability --------------------------------------------------
    def _declared_tools(self) -> set[str]:
        """The tool GROUPS this role declares.

        Absent or empty means "workspace": that was the de-facto behaviour of
        every registry before this key was read, so it must stay the default.
        """
        declared = self.spec.get("tools")
        if not declared:
            return {"workspace"}
        return {str(t).lower() for t in declared}

    def allows_write(self) -> bool:
        """Whether this role may be offered — or use — ANY mutating tool.

        Capability rather than compliance, deliberately: this node overrides
        prose constraints (0/8 on an explicit read-only instruction), so the way
        to make a role read-only is to not hand it the tool. Every tool in
        `_MUTATING_TOOLS` ALSO refuses when this is False, because a model can
        emit a call for a tool it was never offered and "not offered" is not by
        itself an enforcement.

        No spec at all (a legacy direct call) leaves write access unchanged.
        """
        if not self.spec:
            return True
        return bool(self.spec.get("write", True))

    # --- tools (each returns a string for the LLM) ------------------------
    def list_tree(self, rel: str = ".", depth: int = 3) -> str:
        """Return an indented tree of the repo (skipping vendored/build dirs).

        A sibling the role's glob reaches can be listed too - see `_resolve_for_read`. The listing
        keeps the `../` prefix the caller used, because that is the only spelling the read tools
        accept, and a listing the reader cannot act on is a listing that wastes a round.
        """
        start = self._resolve_for_read(rel)
        if not start.exists():
            return f"ERROR: no such path: {rel}"
        sibling = start != self.root and self.root not in start.parents
        lines: list[str] = []

        def walk(d: Path, level: int):
            if level > depth:
                return
            entries = sorted(d.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
            for e in entries:
                if e.name in _SKIP_DIRS or e.suffix.lower() in _SKIP_EXTS:
                    continue
                # In a SIBLING, list only what the read layer will accept. Showing `.github/` and
                # then refusing to open it costs a round and teaches the model nothing - and the
                # listing is the first thing it tries, so the refusal looks like the whole tree.
                # Inside the root nothing is hidden: reads there are exactly what they were.
                if sibling and _read_denial(e.relative_to(start).as_posix()):
                    continue
                lines.append("  " * level + ("📄 " if e.is_file() else "📁 ") + e.name)
                if e.is_dir():
                    walk(e, level + 1)

        lines.append(f"📁 {rel or '.'}")
        walk(start, 1)
        return "\n".join(lines) if lines else "(empty)"

    def read_file(self, rel: str, start: int | None = None,
                  end: int | None = None) -> str:
        """Return file contents — optionally just a 1-based inclusive line range.

        Without a range the whole file is returned, capped at MAX_READ_CHARS.
        WITH a range only those lines are read, so a large file can be inspected
        in bounded slices instead of being truncated mid-file and re-read. The
        range is clamped to the file, and a range that lands past the end is an
        error rather than an empty success.

        A RANGE BOUNDS LINES, NOT CHARS, so both halves stay bounded here: a line
        longer than MAX_LINE_CHARS is elided with a marker naming the line and its
        real length, and a selection larger than MAX_READ_CHARS is elided in the
        middle with a marker saying to narrow the range. Neither is silent — a
        hidden elision is how a model comes to believe it read something it did not.

        Every returned line carries its 1-based number (`  12| text`), so the reader
        can CITE a line rather than count to it — see `_numbered`. Added 2026-09-20.

        A sibling the role's glob reaches can be read too (C2, 2026-09-20) - see
        `_resolve_for_read` for the rule and `_read_denial` for what stays out.
        """
        p = self._resolve_for_read(rel)
        if not p.is_file():
            return f"ERROR: not a file: {rel}"
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return f"ERROR reading {rel}: {e}"

        if start is None and end is None:
            all_lines = text.splitlines()
            body = _numbered(all_lines, 1, len(all_lines), len(all_lines))
            if len(body) > MAX_READ_CHARS:
                body = body[:MAX_READ_CHARS] + "\n…[truncated]"
            return f"--- {rel} ---\n{body}"

        try:
            lines = text.splitlines()
            total = len(lines)
            lo = 1 if start is None else int(start)
            hi = total if end is None else int(end)
        except (TypeError, ValueError):
            return (f"ERROR: start/end must be integers "
                    f"(got start={start!r}, end={end!r})")
        lo = max(lo, 1)
        hi = min(hi, total)
        if lo > hi:
            return (f"ERROR: empty range {start}-{end} for {rel} "
                    f"(file has {total} lines; ranges are 1-based inclusive)")
        body = _numbered(lines, lo, hi, total)
        note = ""
        if len(body) > MAX_READ_CHARS:
            # Head AND tail, for the reason the command layer clips that way: a file's shape
            # is at the top, and a tail read is a real request. The marker names the fix.
            head = MAX_READ_CHARS // 2
            tail = MAX_READ_CHARS - head
            note = " [capped]"
            body = (f"{body[:head]}\n…[elided {len(body) - MAX_READ_CHARS} chars between "
                    f"lines {lo} and {hi}; narrow the range with start/end]…\n{body[-tail:]}")
        return f"--- {rel} [lines {lo}-{hi} of {total}]{note} ---\n{body}"

    def glob(self, pattern: str) -> str:
        """Return repo-relative paths matching a glob (e.g. 'apps/frontend/src/**/*.test.*').

        **A sibling root is searched when the PATTERN NAMES IT** (C2, 2026-09-20), so
        `glob("../repos/solar-sandbox/src/*.js")` works for a role whose glob reaches there, and
        the matches come back with the same `../` prefix - which is what makes them usable by
        `read_file`. A bare `**/*.js` still searches only the repo root.

        **Prefix-routed rather than searched-everywhere, deliberately.** A pattern is a request
        for a place; silently widening it to a second tree would make the result set a thing the
        caller did not ask for, and `../repos/...` in the answer would look like a bug.
        """
        matches: list[str] = []
        for base, prefix, pat in self._read_roots(pattern):
            for p in base.rglob("*"):
                if not p.is_file():
                    continue
                if any(part in _SKIP_DIRS for part in p.relative_to(base).parts):
                    continue
                if p.suffix.lower() in _SKIP_EXTS:
                    continue
                rel = str(p.relative_to(base)).replace("\\", "/")
                if not (fnmatch.fnmatch(p.as_posix(), pat) or fnmatch.fnmatch(rel, pat)):
                    continue
                # A denied path is not MATCHED rather than matched-and-refused: the model would
                # otherwise spend a round on a read it cannot complete, which is the failure the
                # write-only grant already taught.
                if prefix and _read_denial(prefix + rel):
                    continue
                matches.append(prefix + rel)
        matches.sort()
        return "\n".join(matches[:200]) or "(no matches)"

    def _read_roots(self, pattern: str) -> list[tuple[Path, str, str]]:
        """The `(base, prefix, remainder)` triples a read-wide pattern routes to.

        **Prefix-routed rather than searched-everywhere, deliberately**, and this is `glob`'s
        rule: a pattern that NAMES a sibling root is searched there, and one that does not stays in
        the repo root. Silently widening a request to a second tree would make the result set a
        thing the caller did not ask for, and `../repos/...` in an answer would look like a bug.

        **ONE home, two callers (2026-09-23).** `glob` and `search_text` need exactly this, and a
        second copy of a routing rule is a second thing to keep in sync - the defect this
        engagement has already paid for twice.
        """
        out = [(self.root, "", pattern)]
        for base, prefix in self._glob_roots():
            if pattern.startswith(prefix):
                out.append((base, prefix, pattern[len(prefix):]))
        return out

    def _sibling_root(self, start: Path) -> tuple[Path | None, str]:
        """`(root, prefix)` when a resolved path sits in a glob-named sibling, else `(None, "")`.

        The prefix is the `../` spelling `list_tree`, `read_file` and `glob` all keep, because a
        hit the reader cannot hand straight back to `read_file` costs a round rather than saving
        one - which is the entire point of the tool that calls this.
        """
        for base, prefix in self._glob_roots():
            if start == base or base in start.parents:
                return base, prefix
        return None, ""

    def _search_files(self, start: Path):
        """Yield `(path, shown)` for every file a search may look in.

        **One place decides what is searchable**, so the file count reported on a MISS is the count
        that was really searched - and an honest miss is half of what `search_text` is for. The
        skips are `glob`'s, for `glob`'s reason: a vendored or build directory, a binary extension,
        and - for a SIBLING only, because that is somebody else's tree - the read deny list.

        `os.walk` rather than `rglob` because the directories are PRUNED rather than enumerated and
        then discarded. A search is called far more often than a listing, and walking a
        `node_modules` in order to throw it away is the cost this tool exists to remove.
        """
        sib, prefix = self._sibling_root(start)
        base = sib if sib is not None else self.root

        if start.is_file():
            yield start, prefix + start.relative_to(base).as_posix()
            return
        for dirpath, dirnames, filenames in os.walk(start):
            dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS)
            here = Path(dirpath)
            for name in sorted(filenames):
                p = here / name
                if p.suffix.lower() in _SKIP_EXTS:
                    continue
                shown = prefix + p.relative_to(base).as_posix()
                if sib is not None and _read_denial(shown):
                    continue
                yield p, shown

    def search_text(self, pattern: str, rel: str = ".", include: str | None = None,
                    ignore_case: bool = False, max_matches: int = 60) -> str:
        """Find lines matching a regex under `rel`. READ-ONLY, and `git grep`-shaped.

        **Why this tool exists - and it is the largest measured lever (T34, 2026-09-23).** The
        `http` runner offers no content search, so a link finds a fact by listing a tree and
        reading whole files, and `messages` is never trimmed: every read is RE-SENT on the next
        round, which makes cumulative input quadratic in the number of rounds. The measured
        baseline is **396 tool calls for one task** at **32,980 prompt tokens per link**. The lever
        is therefore FEWER READS rather than better prompts - and the IDE path, which already had
        `search`, is not the path the cost was taken on.

        **The answer is shaped like `git grep` on purpose.** `path:line: text` means a hit can be
        CITED rather than merely counted, and `read_file(rel, n - 5, n + 5)` on any hit costs one
        call because the number is already in hand. **Every line passes through `_clip_line` at
        `SEARCH_MAX_LINE_CHARS`, not at `read_file`'s budget**, because a hit is a pointer rather
        than a reading: one wide table row would otherwise spend the budget that buys the next ten
        hits, and `read_file(rel, n, n)` returns that line whole.

        **A miss that says how far it looked is the other half of the lever.** `(no matches in 412
        file(s))` is a fact; `(no matches)` is indistinguishable from "the tool did not look", and
        the model pays a round to find out. It is the same reason both caps name themselves rather
        than truncating silently.

        Routing is `glob`'s, through `_read_roots`' sibling rule: `rel` may name a glob-covered
        sibling (`../repos/<name>`), and inside the root reads are exactly what they were.
        """
        if not str(pattern).strip():
            return ("ERROR: refusing an empty pattern - it matches every line of every file. "
                    "Pass a regex, e.g. 'def search_text' or 'class Workspace'.")
        try:
            rx = re.compile(pattern, re.IGNORECASE if ignore_case else 0)
        except re.error as e:
            return (f"ERROR: bad regex {pattern!r}: {e}. Nothing was searched - fix the pattern "
                    f"rather than falling back to reading files one at a time.")
        try:
            limit = int(max_matches)
        except (TypeError, ValueError):
            return f"ERROR: max_matches must be an integer (got {max_matches!r})"
        limit = max(1, limit)

        start = self._resolve_for_read(rel)
        if not start.exists():
            return f"ERROR: no such path: {rel}"

        hits: list[str] = []
        files = 0
        chars = 0
        stopped = ""
        for p, shown in self._search_files(start):
            # `include` is tried against BOTH spellings - the repo-relative path and the bare name
            # - so `*.py` and `scripts/*.py` both work and the caller does not have to know which
            # one this wants. One call narrows; two calls is the cost the tool is here to remove.
            if include and not (fnmatch.fnmatch(shown, include)
                                or fnmatch.fnmatch(p.name, include)):
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "\x00" in text:
                continue                        # a binary that happens to decode as text
            files += 1
            for n, line in enumerate(text.splitlines(), 1):
                if not rx.search(line):
                    continue
                rendered = f"{shown}:{n}: {_clip_line(line, n, SEARCH_MAX_LINE_CHARS)}"
                # The budget is consulted only once a hit EXISTS, so one enormous matching line
                # can never turn a real match into a reported miss.
                if hits and chars + len(rendered) + 1 > SEARCH_MAX_CHARS:
                    stopped = (f"{len(hits)} hit(s) held under a {SEARCH_MAX_CHARS}-char budget; "
                               f"narrow with rel= or include=, or tighten the pattern")
                    break
                hits.append(rendered)
                chars += len(rendered) + 1
                if len(hits) >= limit:
                    stopped = (f"stopped at max_matches={limit}; raise it, or narrow with rel= or "
                               f"include=")
                    break
            if stopped:
                break

        opts = (" (ignore case)" if ignore_case else "") + (
            f" (include={include})" if include else "")
        # A stopped search examined only PART of the tree, and the header must say so: `13 match(es)
        # in 17 file(s)` on a 187-file tree reads as a complete answer to anyone who does not
        # scroll to the marker. On a miss the walk always ran to the end, so that count is exact.
        scope = f"the first {files} file(s) examined" if stopped else f"{files} file(s)"
        head = (f"--- search: {pattern!r} under {rel}{opts} - {len(hits)} match(es) in "
                f"{scope} ---")
        if not hits:
            return f"{head}\n(no matches in {files} file(s); every line of each was checked)"
        body = "\n".join(hits)
        return f"{head}\n{body}" + (f"\n…[{stopped}]" if stopped else "")

    def write_file(self, rel: str, content: str) -> str:
        """Create/overwrite a file inside the repo, or in a glob-named sibling.

        Four refusals, all structural: a role that is not permitted to write at all, a path
        that escapes the repo root AND is covered by no `write_glob`, and a path on the
        write policy (unconditional deny-list, per-role deny, or outside the role's scope).
        """
        if not self.allows_write():
            return (f"ERROR: refusing to write {rel}: this role is read-only "
                    f"(`write` is false in the registry)")
        try:
            p, inside = self._resolve_for_write(rel)
        except (OSError, ValueError) as e:
            return f"ERROR: refusing to write {rel}: {e}"
        denial = self._write_denial(rel)
        if denial:
            return f"ERROR: refusing to write {rel}: {denial}"
        if not inside and not self._glob_allows(rel):
            return f"ERROR: refusing to write {rel}: path escapes repo root: {rel!r}"
        if p.is_dir():
            return f"ERROR: {rel} is a directory"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"wrote {rel} ({len(content)} chars)"

    def replace_in_file(self, rel: str, old_string: str, new_string: str) -> str:
        """Replace ONE uniquely-anchored passage inside an EXISTING file, in place.

        **Added 2026-09-21, because its absence made a whole class of edit impossible and the
        only workaround DESTROYED a file.** `write_file` is this layer's only mutator and it
        OVERWRITES, so the sole way to change two lines of a 101 KB JSON catalog was to
        reconstruct all 2746 lines out of reads capped at `MAX_READ_CHARS`, then write the whole
        thing back. Measured in the Promyro engagement that day: an `implementer` link took that
        route on a message catalog and returned **820 lines, deleting 2690 of them**. Four further
        attempts on the same two catalogs changed nothing at all, and the fifth refused in as many
        words - *"the only file-mutating tool available to me is `write_file`, which overwrites the
        whole file"*. **A role that cannot make a bounded edit makes an unbounded one.**

        Safe by construction rather than by instruction, which is the whole point:

        - the target must already EXIST - this tool edits, it never creates, so it cannot be used
          to truncate a file into existence;
        - the anchor must occur EXACTLY ONCE. Zero matches and two matches are both refusals with
          NOTHING written, so an ambiguous anchor can never edit the wrong occurrence;
        - nothing outside the anchor is touched, which is what makes a 101 KB file as cheap and as
          safe to edit as a 4 KB one - size stops being a factor in whether the edit is possible.

        The same refusals as `write_file` run first, through the same helpers, so a role's
        `write_scope`, its own denies and the unconditional deny list all apply unchanged.

        Line endings are PRESERVED: the file is opened with `newline=""` on both sides, so a
        working tree the repo keeps in LF does not come back in CRLF. The search is therefore on
        the raw text, and an anchor that spans a line break will not match a file using the other
        convention - keep anchors inside one line where you can.
        """
        if not self.allows_write():
            return (f"ERROR: refusing to edit {rel}: this role is read-only "
                    f"(`write` is false in the registry)")
        try:
            p, inside = self._resolve_for_write(rel)
        except (OSError, ValueError) as e:
            return f"ERROR: refusing to edit {rel}: {e}"
        denial = self._write_denial(rel)
        if denial:
            return f"ERROR: refusing to edit {rel}: {denial}"
        if not inside and not self._glob_allows(rel):
            return f"ERROR: refusing to edit {rel}: path escapes repo root: {rel!r}"
        if not p.is_file():
            return f"ERROR: not a file: {rel}"
        if old_string == "":
            return f"ERROR: refusing to edit {rel}: old_string is empty"
        try:
            with open(p, "r", encoding="utf-8", newline="") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError) as e:
            return f"ERROR reading {rel}: {e}"
        found = text.count(old_string)
        if found == 0:
            return (f"ERROR: refusing to edit {rel}: old_string not found - "
                    f"nothing was written. Read the exact text first.")
        if found > 1:
            return (f"ERROR: refusing to edit {rel}: old_string occurs {found} times - "
                    f"nothing was written. Include more surrounding text so it is unique.")
        try:
            with open(p, "w", encoding="utf-8", newline="") as fh:
                fh.write(text.replace(old_string, new_string, 1))
        except OSError as e:
            return f"ERROR writing {rel}: {e}"
        return (f"edited {rel}: 1 occurrence, {len(old_string)} -> {len(new_string)} chars "
                f"({len(text)} -> {len(text) - len(old_string) + len(new_string)} chars)")

    # --- OpenAI-compatible function schema --------------------------------
    _TOOL_NAMES = ("list_tree", "read_file", "glob", "search_text", "write_file",
                   "replace_in_file")

    # Every tool that MUTATES the tree, in ONE place (2026-09-21): a read-only role must be offered
    # none of them, and a second copy of this set is a second thing to keep in sync - which is how
    # the shipped default install came to hand `write_file` to `reviewer` (see registry.py).
    _MUTATING_TOOLS = ("write_file", "replace_in_file")

    def handles(self, name: str) -> bool:
        """Whether this layer owns a tool name (used by the executor's composite)."""
        return name in self._TOOL_NAMES

    def tool_schemas(self) -> list[dict]:
        """The function schemas for the tools THIS role may be offered.

        Gated by the role. A read-only role is never handed any tool in
        `_MUTATING_TOOLS`: a tool that is not in the list cannot be argued into
        use, and this node overrides prose constraints (0/8 on an explicit
        read-only instruction).
        """
        schemas = [
            {"type": "function", "function": {
                "name": "list_tree",
                "description": "List the repo directory tree (skips vendored/build dirs).",
                "parameters": {"type": "object", "properties": {
                    "rel": {"type": "string", "description": "repo-relative dir, default '.'"},
                    "depth": {"type": "integer", "description": "max depth, default 3"}},
                    "required": []}}},
            {"type": "function", "function": {
                "name": "read_file",
                "description": ("Read a file inside the repo. Returns the whole file "
                                "(truncated at 40000 chars) unless start/end give a "
                                "1-based inclusive line range, in which case only "
                                "those lines are returned — prefer a range over "
                                "re-reading a large file. A very long line, or a range "
                                "larger than the read budget, is elided with a marker "
                                "saying so; narrow the range rather than assuming the "
                                "file continues past it."),
                "parameters": {"type": "object", "properties": {
                    "rel": {"type": "string", "description": "repo-relative file path"},
                    "start": {"type": "integer", "description": "first line, 1-based (optional)"},
                    "end": {"type": "integer", "description": "last line, inclusive (optional)"}},
                    "required": ["rel"]}}},
            {"type": "function", "function": {
                "name": "glob",
                "description": "Find files matching a glob pattern inside the repo.",
                "parameters": {"type": "object", "properties": {
                    "pattern": {"type": "string", "description": "glob, e.g. '**/*.test.ts'"}},
                    "required": ["pattern"]}}},
            {"type": "function", "function": {
                "name": "search_text",
                "description": ("Search file CONTENTS with a regex and return `path:line: text`, "
                                "the shape git grep prints. USE THIS FIRST: one call finds a "
                                "symbol, a string or a citation anywhere in the tree, where "
                                "reading files one at a time costs a round each and every read "
                                "is re-sent afterwards. Bounded by max_matches and by a "
                                "character budget, and it names the limit it hit - narrow with "
                                "`rel` or `include` instead of re-running the same search. "
                                "`(no matches in N file(s))` means the search RAN across N "
                                "files and found nothing; it is not a failure."),
                "parameters": {"type": "object", "properties": {
                    "pattern": {"type": "string", "description": "regex, e.g. 'def search' or 'T34'"},
                    "rel": {"type": "string", "description": "repo-relative dir or file to search under, default '.'"},
                    "include": {"type": "string", "description": "glob for the path, e.g. '*.py' (optional)"},
                    "ignore_case": {"type": "boolean", "description": "case-insensitive (default false)"},
                    "max_matches": {"type": "integer", "description": "stop after this many hits, default 60"}},
                    "required": ["pattern"]}}},
            {"type": "function", "function": {
                "name": "write_file",
                "description": ("Create or overwrite a WHOLE file inside the repo. If the file "
                                "already exists, prefer replace_in_file: this one rewrites "
                                "every byte, so anything you did not read back is lost."),
                "parameters": {"type": "object", "properties": {
                    "rel": {"type": "string", "description": "repo-relative file path"},
                    "content": {"type": "string", "description": "full file content"}},
                    "required": ["rel", "content"]}}},
            {"type": "function", "function": {
                "name": "replace_in_file",
                "description": ("Change ONE passage inside an EXISTING file, in place. Use this "
                                "rather than write_file for any file bigger than one read: it "
                                "never rewrites the file, so a 100 KB file is as cheap and as "
                                "safe to change as a 1 KB one. old_string must occur EXACTLY "
                                "once - no match, or more than one, is refused and nothing is "
                                "written. Read the file first and copy the text exactly; keep "
                                "the anchor inside a single line."),
                "parameters": {"type": "object", "properties": {
                    "rel": {"type": "string", "description": "repo-relative file path"},
                    "old_string": {"type": "string", "description": "exact text to find; must occur exactly once"},
                    "new_string": {"type": "string", "description": "text to replace it with"}},
                    "required": ["rel", "old_string", "new_string"]}}},
        ]
        if "workspace" not in self._declared_tools():
            return []
        # **The model cannot guess where it may go, and the first version of this grant made it find
        # out by failing.** Measured 2026-09-20: the agent tried `list_tree`, `read_file` and `glob`
        # on the sibling, was refused by all three, concluded that a write it knows will be rejected
        # "is not a test of anything", and wrote nothing. Naming the roots in the description costs
        # ~60 bytes on the three tools that are affected and removes that round entirely.
        reach = [prefix for _base, prefix in self._glob_roots()]
        if reach:
            note = (f" Reachable siblings: {', '.join(reach)} "
                    f"(this role's `write_glob`; reads there are granted, writes too).")
            for s in schemas:
                if s["function"]["name"] in ("list_tree", "read_file", "glob", "search_text"):
                    s["function"]["description"] += note
        if not self.allows_write():
            return [s for s in schemas
                    if s["function"]["name"] not in self._MUTATING_TOOLS]
        return schemas

    def call_tool(self, name: str, args: dict) -> str:
        fn = getattr(self, name, None)
        if fn is None:
            return f"ERROR: unknown tool {name}"
        try:
            return fn(**args)
        except TypeError as e:
            return f"ERROR: bad args for {name}: {e}"
        except ValueError as e:
            return f"ERROR: {e}"
