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


class Workspace:
    """Repo-bounded file access for one governor run.

    `spec` is the ROLE's registry entry (v5 §6), passed in by the executor so
    policy can be derived from the role rather than the process. It is carried
    but not yet read — the write policy (B2) and the offered tool set (B1) are
    what consume it. Deep-copied so a caller's registry dict is never mutated.
    """

    def __init__(self, root: Path, spec: dict | None = None):
        self.root = Path(root).expanduser().resolve()
        self.spec = copy.deepcopy(spec) if spec else {}

    # --- guards -----------------------------------------------------------
    def _resolve(self, rel: str) -> Path:
        """Resolve a repo-relative path and enforce confinement to root."""
        p = (self.root / rel).resolve()
        if p != self.root and self.root not in p.parents:
            raise ValueError(f"path escapes repo root: {rel!r}")
        return p

    def _write_denial(self, rel: str) -> str | None:
        """Why `rel` may not be written, or None when it may.

        This is the light profile's only write guard, so it is deliberately
        unconditional: it does not consult the role, the objective, or anything
        the model can influence. A deny here is not a suggestion.
        """
        parts = [p for p in rel.replace("\\", "/").split("/") if p not in ("", ".")]
        for part in parts[:-1]:
            if part.lower() in _WRITE_DENY_DIRS:
                return f"{part}/ is protected (agent config / repo metadata)"
        name = parts[-1] if parts else ""
        if name.lower() in _WRITE_DENY_NAMES:
            return f"{name} is protected (defines tooling, deps or CI)"
        return None

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
        """
        p = self._resolve(rel)
        if not p.is_file():
            return f"ERROR: not a file: {rel}"
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return f"ERROR reading {rel}: {e}"

        if start is None and end is None:
            if len(text) > MAX_READ_CHARS:
                text = text[:MAX_READ_CHARS] + "\n…[truncated]"
            return f"--- {rel} ---\n{text}"

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
        body = "\n".join(lines[lo - 1:hi])
        return f"--- {rel} [lines {lo}-{hi} of {total}] ---\n{body}"

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
        """Create/overwrite a file inside the repo.

        Two refusals, both structural: a path that escapes the repo root, and a
        path on the write deny-list. The deny-list is what stops an injected
        objective from rewriting the agent's own registry entry.
        """
        try:
            p = self._resolve(rel)
        except ValueError as e:
            return f"ERROR: {e}"
        denial = self._write_denial(rel)
        if denial:
            return f"ERROR: refusing to write {rel}: {denial}"
        if p.is_dir():
            return f"ERROR: {rel} is a directory"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"wrote {rel} ({len(content)} chars)"

    # --- OpenAI-compatible function schema --------------------------------
    def tool_schemas(self) -> list[dict]:
        return [
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
                                "re-reading a large file."),
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
