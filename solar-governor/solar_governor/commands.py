"""Vetted command vocabulary (patch Part C): a closed set of repo-declared commands.

Why a vocabulary and not a shell: on the `http` runner there is no supervisor. A model
that can COMPOSE a command string can do anything the process can; a model that can only
NAME one of N repo-declared argv vectors is bounded by what the repo already runs. There
is no free-text command field and no free-text argument field. The only prose a human is
ever asked to act on comes from config (`describe`), never from the model.

Absence is the mechanism. `npm run format` is not in a Promyro vocabulary because the
implementer prompt forbids it (it reformats the client's whole tree) - not because a rule
asks the model to avoid it. This node overrides prose rules, so a rule is not containment.

Windows: `shell=False` cannot execute a `.CMD`/`.BAT` shim. `["npm", "--version"]` raises
WinError 2 while `["git", "--version"]` succeeds, because git is a real `.EXE`. argv[0] is
therefore resolved with `shutil.which` (which returns `npm.CMD`) and the RESOLVED path is
what gets executed - never the bare name.

Not granted is not the same as not declared, and the error says which, so a role that
genuinely needs a command reports a fixable problem instead of guessing.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from .workspace import resolve_in_root

TOOL_NAME = "run_command"

DEFAULT_TIMEOUT = 60
MAX_TIMEOUT = 900
DEFAULT_MAX_OUTPUT = 4000
MAX_OUTPUT_CEILING = 40_000
DEFAULT_MAX_ITEMS = 15
LINE_CAP = 400

VALID_KINDS = ("read", "check", "act")

# Tool output arrives coloured. Escape sequences are wasted tokens and they obscure the
# text a model has to read, so they are stripped before anything else looks at it.
_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")

# On a NON-ZERO exit, lines that usually carry the reason. Only consulted for failures:
# the exit code is the reliable pass/fail signal, and line-matching on a PASSING checker
# produces false positives (a clean `next lint` emits nine 'error'-ish lines of info text,
# measured 2026-09-18). A repo can override this with `shape.keep`.
_FAILURE_HINT = re.compile(
    r"(\berror\b|\berrors\b|✖|✘|×|✗|\bFAIL\b|not ok|expected|assert|\bTS\d{4}\b|"
    r"\bCannot find\b|\bexited with\b|\bcommand not found\b|_test\.|\.test\.|\.spec\.|"
    r"\[warn\]|\bWarning\b)",
    re.I)


def vocabulary_path(root: Path) -> Path:
    """Where a repo declares its command vocabulary."""
    return Path(root) / ".solar" / "commands.json"


def load_vocabulary(root: Path) -> dict:
    """Load `.solar/commands.json`, keeping only well-formed entries.

    A malformed entry is dropped rather than raising: a broken vocabulary must not
    take the whole run down, and an entry with no argv can never be executed anyway.
    """
    path = vocabulary_path(root)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        str(name): spec for name, spec in data.items()
        if isinstance(spec, dict) and isinstance(spec.get("argv"), list) and spec["argv"]
    }


def _bounded_int(value, default: int, low: int, high: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, n))


def _clip(text: str, cap: int) -> str:
    """Keep the head AND the tail: a checker's failure list starts early and its
    summary lands last, so trimming only one end hides the part that matters."""
    if len(text) <= cap:
        return text
    head = cap // 2
    tail = cap - head
    return f"{text[:head]}\n…[{len(text) - cap} chars elided]…\n{text[-tail:]}"


def strip_ansi(text: str) -> str:
    """Drop terminal colour escapes - they are tokens spent on nothing."""
    return _ANSI.sub("", text)


def _exit_code(code: int) -> int:
    """Windows reports a 32-bit DWORD, so a failure can surface as 4294963238.
    Reading that teaches a model nothing; it is normalised to the signed value."""
    return code - 2 ** 32 if code > 2 ** 31 - 1 else code


def _shape_check(stdout: str, stderr: str, returncode: int, spec: dict,
                 cap: int) -> list[str]:
    """CHECK output, shaped: failures only.

    Grounded in measurement on a real Next.js monorepo (2026-09-18): a PASSING
    `npm --silent run typecheck` emits 0 chars, and a FAILING `prettier --check .`
    emits ~31k chars of which the only actionable line is the last ("Code style
    issues found in 580 files"). Unshaped failure reports also cost +10% prompt
    tokens with more rounds (16 §11.3), so shaping is what makes a check actionable
    rather than merely present.

    `shape.summary_only` keeps just the final line (right for a formatter that lists
    every file); `shape.keep` is a repo-supplied regex; `shape.max_items` caps the list.
    """
    if returncode == 0:
        return ["result: PASSED"]

    body = "\n".join(x for x in (stdout, stderr) if x.strip()).strip()
    raw = [ln.rstrip() for ln in body.splitlines() if ln.strip()]
    if not raw:
        return ["result: FAILED (the command produced no output)"]

    shape = spec.get("shape") or {}
    max_items = _bounded_int(shape.get("max_items"), DEFAULT_MAX_ITEMS, 1, 200)

    if shape.get("summary_only"):
        kept = raw[-1:]
    else:
        keep = shape.get("keep")
        pattern = re.compile(keep, re.I) if keep else _FAILURE_HINT
        kept = [ln for ln in raw if pattern.search(ln)][:max_items]
        if raw[-1] not in kept:
            kept.append(raw[-1])

    kept = [_clip(ln, LINE_CAP) for ln in kept]
    out = [f"--- failures ({len(kept)} of {len(raw)} lines) ---"] + kept
    suppressed = len(raw) - len(kept)
    if suppressed > 0:
        out.append(f"…[{suppressed} further line(s) suppressed]")
    return out


class CommandRunner:
    """The `exec` tool group, bounded by a repo-declared vocabulary.

    Grants are per ROLE (`exec_allow` in the registry). With no spec - or a spec with
    no `exec_allow` - nothing is granted, so no command tool is advertised at all.
    That default is deliberately the opposite of `write` (which defaults to allowed,
    for backward compatibility): exec is new, no existing registry could have relied
    on it, and it is the capability that most needs to be opt-in.
    """

    def __init__(self, root: Path, spec: dict | None = None,
                 vocabulary: dict | None = None, human_approval: bool = False):
        self.root = Path(root).expanduser().resolve()
        self.spec = copy.deepcopy(spec) if spec else {}
        self.vocabulary = (load_vocabulary(self.root)
                           if vocabulary is None else vocabulary)
        self.human_approval = bool(human_approval)

    # --- surface ----------------------------------------------------------
    def handles(self, name: str) -> bool:
        return name == TOOL_NAME

    def granted(self) -> dict:
        """The vocabulary entries this role may actually run."""
        allowed = self.spec.get("exec_allow") or []
        return {str(n): self.vocabulary[str(n)] for n in allowed
                if str(n) in self.vocabulary}

    def tool_schemas(self) -> list[dict]:
        names = sorted(self.granted())
        if not names:
            return []
        return [{"type": "function", "function": {
            "name": TOOL_NAME,
            "description": ("Run one of this repo's declared read/check commands. You "
                            "cannot supply a command or its arguments - only a name. "
                            "Available: " + ", ".join(names)),
            "parameters": {"type": "object", "properties": {
                "command": {"type": "string", "enum": names,
                            "description": "which declared command to run"}},
                "required": ["command"]}}}]

    def call_tool(self, name: str, args: dict) -> str:
        if name != TOOL_NAME:
            return f"ERROR: unknown tool {name}"
        try:
            return self.run_command(**(args or {}))
        except TypeError as e:
            return f"ERROR: bad args for {name}: {e}"

    # --- execution --------------------------------------------------------
    def run_command(self, command: str) -> str:
        spec = self.granted().get(str(command))
        if spec is None:
            why = ("declared in .solar/commands.json but not granted to this role"
                   if str(command) in self.vocabulary
                   else "not declared in .solar/commands.json")
            return f"ERROR: command {command!r} is not available ({why})"

        declared = [str(a) for a in spec["argv"]]
        exe = shutil.which(declared[0])
        if exe is None:
            return (f"ERROR: command not available: {declared[0]!r} is not installed "
                    f"or not on PATH on this machine")
        argv = [exe] + declared[1:]

        kind = str(spec.get("kind", "read"))
        if kind not in VALID_KINDS:
            return f"ERROR: {command!r} declares an invalid kind {kind!r}"

        try:
            cwd = self._cwd(spec)
        except ValueError as e:
            return f"ERROR: {e}"

        # Part D: an acting command does not run without a human decision.
        if kind == "act" and self.human_approval:
            return self._await_approval(str(command), spec, declared, argv, cwd)

        return self._execute(str(command), spec, declared, argv, cwd)

    def _cwd(self, spec: dict) -> Path:
        """The command's working directory: repo-relative, confined to the repo."""
        rel = str(spec.get("cwd") or ".").strip() or "."
        path = resolve_in_root(self.root, rel)
        if not path.is_dir():
            raise ValueError(f"cwd is not a directory inside the repo: {rel!r}")
        return path

    def _execute(self, command: str, spec: dict, declared: list[str],
                 argv: list[str], cwd: Path) -> str:
        timeout = _bounded_int(spec.get("timeout"), DEFAULT_TIMEOUT, 1, MAX_TIMEOUT)
        # env additions are for THIS child only - never os.environ, never the shell
        env = dict(os.environ)
        for key, value in (spec.get("env") or {}).items():
            env[str(key)] = str(value)

        started = time.monotonic()
        try:
            proc = subprocess.run(argv, cwd=str(cwd), env=env, shell=False,
                                  capture_output=True, text=True, errors="replace",
                                  timeout=timeout)
        except subprocess.TimeoutExpired:
            return (f"[{command}] TIMEOUT after {timeout}s (kind={spec.get('kind', 'read')})\n"
                    f"argv: {' '.join(declared)}")
        except OSError as e:
            return f"[{command}] ERROR: could not execute: {e}"
        elapsed = time.monotonic() - started

        cap = _bounded_int(spec.get("max_output"), DEFAULT_MAX_OUTPUT, 200,
                           MAX_OUTPUT_CEILING)
        # escapes off first: --silent removes npm's banner, but a script's own output
        # still arrives coloured
        out = strip_ansi(proc.stdout or "")
        err = strip_ansi(proc.stderr or "")
        try:
            shown_cwd = str(cwd.relative_to(self.root)) or "."
        except ValueError:
            shown_cwd = "."

        kind = spec.get("kind", "read")
        verdict = "PASS" if proc.returncode == 0 else "FAIL"
        lines = [f"[{command}] {verdict} exit {_exit_code(proc.returncode)} "
                 f"in {elapsed:.1f}s (kind={kind}, cwd={shown_cwd})"]
        if spec.get("describe"):
            lines.append(f"note: {spec['describe']}")

        if kind == "check":
            lines += _shape_check(out, err, proc.returncode, spec, cap)
        else:
            # a READ command's output IS the information - never summarise it
            lines += ["--- stdout ---", _clip(out, cap).strip() or "(empty)"]
            if err.strip():
                lines += ["--- stderr ---", _clip(err, cap).strip()]
        return "\n".join(lines)

    # --- Part D: the approval gate ----------------------------------------
    def _await_approval(self, command: str, spec: dict, declared: list[str],
                        argv: list[str], cwd: Path) -> str:
        """Propose, then STOP. Modelled on `write_handoff`'s propose -> human -> resume.

        The id is derived from the command, not the round, so a decision written by a
        human is still found on the next attempt rather than re-asked. Everything a
        human reads is derived from CONFIG - the model contributes no text here.
        """
        adir = self.root / ".solar" / "approvals"
        adir.mkdir(parents=True, exist_ok=True)
        key = f"{command}|{' '.join(argv)}|{cwd}"
        aid = hashlib.md5(key.encode("utf-8")).hexdigest()[:8]
        decision = adir / f"{aid}.decision"

        if decision.is_file():
            text = decision.read_text(encoding="utf-8", errors="replace").strip()
            if text.lower().startswith("allow"):
                return self._execute(command, spec, declared, argv, cwd)
            reason = text.split(":", 1)[1].strip() if ":" in text else "no reason given"
            return (f"DENIED: {reason}\nDo not retry this command. Adapt, or report "
                    f"that it is blocked.")

        proposal = adir / f"{aid}.md"
        if not proposal.is_file():
            proposal.write_text(self._proposal(command, spec, declared, cwd, aid),
                                encoding="utf-8")
        return (f"AWAITING APPROVAL {aid}\n"
                f"An acting command does not run without a human decision. A human must "
                f"write 'allow' or 'deny: <reason>' to .solar/approvals/{aid}.decision. "
                f"You cannot proceed and retrying will not help - report that you are "
                f"waiting on approval.")

    def _proposal(self, command: str, spec: dict, declared: list[str],
                  cwd: Path, aid: str) -> str:
        try:
            shown_cwd = str(cwd.relative_to(self.root)) or "."
        except ValueError:
            shown_cwd = "."
        return (
            f"# Command approval requested - {command}\n\n"
            f"| field | value |\n| :--- | :--- |\n"
            f"| id | `{aid}` |\n"
            f"| command | `{command}` |\n"
            f"| argv | `{' '.join(declared)}` |\n"
            f"| cwd | `{shown_cwd}` |\n"
            f"| kind | `{spec.get('kind')}` |\n"
            f"| timeout | `{spec.get('timeout', DEFAULT_TIMEOUT)}s` |\n\n"
            f"**What it does (from `.solar/commands.json`, not from the model):**\n\n"
            f"> {spec.get('describe') or '(no describe string declared)'}\n\n"
            f"To decide, write one of these to `.solar/approvals/{aid}.decision`:\n\n"
            f"```\nallow\n```\n\n```\ndeny: <reason>\n```\n\n"
            f"Everything above is derived from the repo's declared vocabulary. The "
            f"running model did not author any of it.\n"
        )
