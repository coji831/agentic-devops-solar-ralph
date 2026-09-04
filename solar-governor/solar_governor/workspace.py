"""Workspace tool layer (v5 tool layer, light subset): repo-bounded read/glob/
write helpers exposed to the model executor as function tools.

Sovereignty guard (v5 §11): every path is resolved and confined to the repo
root; writes refuse paths that escape it. No shell/exec here (light profile).
"""
from __future__ import annotations

import fnmatch
from pathlib import Path

# dirs never surfaced / written, even inside the repo
_SKIP_DIRS = {".git", "node_modules", ".solar", ".next", "dist", "build",
              "__pycache__", ".venv", "venv", "coverage", ".terraform", ".cache"}
_SKIP_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff",
              ".woff2", ".ttf", ".eot", ".map", ".sqlite", ".db", ".lock"}
MAX_READ_CHARS = 40_000


class Workspace:
    """Repo-bounded file access for one governor run."""

    def __init__(self, root: Path):
        self.root = Path(root).expanduser().resolve()

    # --- guards -----------------------------------------------------------
    def _resolve(self, rel: str) -> Path:
        """Resolve a repo-relative path and enforce confinement to root."""
        p = (self.root / rel).resolve()
        if p != self.root and self.root not in p.parents:
            raise ValueError(f"path escapes repo root: {rel!r}")
        return p

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

    def read_file(self, rel: str) -> str:
        """Return file contents (truncated). rel is repo-relative."""
        p = self._resolve(rel)
        if not p.is_file():
            return f"ERROR: not a file: {rel}"
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return f"ERROR reading {rel}: {e}"
        if len(text) > MAX_READ_CHARS:
            text = text[:MAX_READ_CHARS] + "\n…[truncated]"
        return f"--- {rel} ---\n{text}"

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
        """Create/overwrite a file inside the repo (write-guard: no escapes)."""
        try:
            p = self._resolve(rel)
        except ValueError as e:
            return f"ERROR: {e}"
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
                "description": "Read a file inside the repo (returns contents, truncated).",
                "parameters": {"type": "object", "properties": {
                    "rel": {"type": "string", "description": "repo-relative file path"}},
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
