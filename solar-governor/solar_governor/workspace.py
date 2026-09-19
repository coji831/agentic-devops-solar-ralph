"""Workspace tool layer (v5 tool layer, light subset): repo-bounded read/glob/
write helpers exposed to the model executor as function tools.

Sovereignty guard (v5 §11): every path is resolved and confined to the repo
root; writes refuse paths that escape it. No shell/exec here (light profile).
"""
from __future__ import annotations

import copy
import fnmatch
from pathlib import Path

# dirs never surfaced / written, even inside the repo
_SKIP_DIRS = {".git", "node_modules", ".solar", ".next", "dist", "build",
              "__pycache__", ".venv", "venv", "coverage", ".terraform", ".cache"}
_SKIP_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff",
              ".woff2", ".ttf", ".eot", ".map", ".sqlite", ".db", ".lock"}
MAX_READ_CHARS = 40_000

# A line is NOT a size bound (TD-5.7-5). `read_file(rel, 1, 60)` on a file whose only line was
# 282,604 chars - a `.tsbuildinfo`, minified JS, a lockfile, a one-line data blob - returned
# 282,669 chars: about 70k tokens against a window a local model has 16k of, and it then stays
# in history for the rest of the run. One line is capped at the size this runtime already gives
# one COMMAND's output (`commands.DEFAULT_MAX_OUTPUT`), and the marker names the line and its
# real length, so the elision is a fact the model can report rather than a silent gap.
MAX_LINE_CHARS = 4_000


def _clip_line(text: str, lineno: int) -> str:
    """One line of a file, bounded, with the elision spelling itself out (see MAX_LINE_CHARS)."""
    if len(text) <= MAX_LINE_CHARS:
        return text
    return (f"{text[:MAX_LINE_CHARS]}…[line {lineno} elided: {len(text)} chars, "
            f"first {MAX_LINE_CHARS} shown]")


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
    """
    return any(fnmatch.fnmatchcase(norm, p) for p in patterns)


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
        """Whether this role may be offered — or use — `write_file` at all.

        Capability rather than compliance, deliberately: this node overrides
        prose constraints (0/8 on an explicit read-only instruction), so the way
        to make a role read-only is to not hand it the tool. `write_file` ALSO
        refuses when this is False, because a model can emit a call for a tool it
        was never offered and "not offered" is not by itself an enforcement.

        No spec at all (a legacy direct call) leaves write access unchanged.
        """
        if not self.spec:
            return True
        return bool(self.spec.get("write", True))

    # --- tools (each returns a string for the LLM) ------------------------
    def list_tree(self, rel: str = ".", depth: int = 3) -> str:
        """Return an indented tree of the repo (skipping vendored/build dirs)."""
        start = self._resolve(rel)
        if not start.exists():
            return f"ERROR: no such path: {rel}"
        lines: list[str] = []

        def walk(d: Path, level: int):
            if level > depth:
                return
            entries = sorted(d.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
            for e in entries:
                if e.name in _SKIP_DIRS or e.suffix.lower() in _SKIP_EXTS:
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
        """
        p = self._resolve(rel)
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
        """Return repo-relative paths matching a glob (e.g. 'apps/frontend/src/**/*.test.*')."""
        matches: list[str] = []
        for p in self.root.rglob("*"):
            if not p.is_file():
                continue
            if any(part in _SKIP_DIRS for part in p.relative_to(self.root).parts):
                continue
            if p.suffix.lower() in _SKIP_EXTS:
                continue
            if fnmatch.fnmatch(p.as_posix(), pattern) or \
               fnmatch.fnmatch(str(p.relative_to(self.root)).replace("\\", "/"), pattern):
                matches.append(str(p.relative_to(self.root)).replace("\\", "/"))
        matches.sort()
        return "\n".join(matches[:200]) or "(no matches)"

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

    # --- OpenAI-compatible function schema --------------------------------
    _TOOL_NAMES = ("list_tree", "read_file", "glob", "write_file")

    def handles(self, name: str) -> bool:
        """Whether this layer owns a tool name (used by the executor's composite)."""
        return name in self._TOOL_NAMES

    def tool_schemas(self) -> list[dict]:
        """The function schemas for the tools THIS role may be offered.

        Gated by the role. A read-only role is never handed `write_file`: a tool
        that is not in the list cannot be argued into use, and this node overrides
        prose constraints (0/8 on an explicit read-only instruction).
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
                "name": "write_file",
                "description": "Create or overwrite a file inside the repo.",
                "parameters": {"type": "object", "properties": {
                    "rel": {"type": "string", "description": "repo-relative file path"},
                    "content": {"type": "string", "description": "full file content"}},
                    "required": ["rel", "content"]}}},
        ]
        if "workspace" not in self._declared_tools():
            return []
        if not self.allows_write():
            return [s for s in schemas
                    if s["function"]["name"] != "write_file"]
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
