"""Vetted command vocabulary (patch Part C): a closed set of repo-declared commands.

Why a vocabulary and not a shell: on the `http` runner there is no supervisor. A model
that can COMPOSE a command string can do anything the process can; a model that can only
NAME one of N repo-declared argv vectors is bounded by what the repo already runs. There
is no free-text command field. **One argument exists, and it is not free text:** a command
declaring `accepts: path` may be handed a path, which is resolved against that command's own
`cwd` and refused unless it names a real file inside it (T40, 2026-09-23). The only prose a
human is ever asked to act on comes from config (`describe`), never from the model.
**A declaration may name the RUN's clone rather than a client's** (T50, 2026-09-23). `"cwd":
"repos/{clone}"` is resolved against the value the run declared, and a run that declared none is
refused at the first call that needs one - see `_cwd`. Twelve entries here were spelled for ONE
client (`pvl_rentals_test` and eleven siblings), so a role working on another clone could take a
PASS from the wrong repository, credited to this run. The entries are now named for what they DO,
the target lives in the RUN, and the repository each call used is still printed on every call.
Absence is the mechanism. `npm run format` is not in a Promyro vocabulary because the
implementer prompt forbids it (it reformats the client's whole tree) - not because a rule
asks the model to avoid it. This node overrides prose rules, so a rule is not containment.
**That absence is about formatting the WHOLE TREE and it stays:** the per-file formatter
added 2026-09-23 checks ONE path a caller names, and cannot ask for `--write` or for a second
target, because the path is APPENDED to a frozen argv rather than composed into one.

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

from .core import read_json
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

# **A DECLARED COMMAND MAY ACCEPT EXACTLY ONE PATH, AND IT IS THE ONLY THING THAT MAY EVER BE ADDED
# TO A FROZEN `argv`** (T40, 2026-09-23). The rule this repository states everywhere else is that
# `argv` is frozen - *"a path written there is a path that can go stale"* - and that rule is not
# weakened here: the path is never WRITTEN in `.solar/commands.json`, it is SUPPLIED by the caller
# and resolved against the command's own `cwd` through the same `resolve_in_root` that confines
# `cwd` itself, so it cannot escape the root and cannot go stale. What it buys is the one command
# the vocabulary was missing: a formatter asked about THE FILE A LINK JUST EDITED, instead of a
# whole-clone run whose failure count is a fact about the tree rather than about the edit - measured
# 2026-09-23, that clone's whole-clone check reports **587 files**, which is why it was documented
# as expected to fail and read as noise.
#
# The vocabulary is CLOSED and has one member. A directory, a glob or a ref is a DIFFERENT argument,
# and it should be declared when something needs it rather than guessed now.
ARG_KINDS = ("path",)

# **THE RUN DECLARES WHICH CLONE IT IS ABOUT, AND A `cwd` MAY NAME IT** (T50, 2026-09-23). A
# declaration that targets a clone writes `"cwd": "repos/{clone}"`; the runtime substitutes the value
# the RUN declared and then confines and existence-checks it exactly as it always has, so the two
# refusals that already guarded `cwd` - `resolve_in_root` for an escape, `is_dir` for a path nobody
# kept - guard the target too.
#
# **The placeholder is the whole vocabulary and it must be the LAST segment.** `repos/{clone}` names
# a clone; `{clone}/src` would name a path inside one, and nothing needs that yet. **What it
# substitutes is a NAME, not a path** (`clone_name_problem`), because a value carrying a separator can
# choose the directory instead of naming one. What the placeholder buys is that a command is no
# longer spelled for one client: twelve entries used to hard-code `pvl-rentals`, so the target was
# the DECLARATION's rather than the run's - which is how a role working on another clone could be
# credited with a pass from the wrong repository.
CLONE = "{clone}"
# **THE RUN'S OTHER LEGAL ANSWER, and it is a word rather than an absence.** A record-keeping run
# touches no clone, and forcing it to name one would recreate the guard's worst failure - "the guard
# said unchanged about a repository the run never touched, and that reads as evidence". So `none` is
# declarable and clone-scoped commands refuse under it; **reserved, because a clone cannot be called
# something the runtime reads as a refusal.**
CLONE_NONE = "none"

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
        data = read_json(path)
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


def declares_clone(spec: dict) -> bool:
    """Whether this declaration's `cwd` names the run's clone."""
    return CLONE in str(spec.get("cwd") or "")


def clone_required(vocabulary: dict) -> bool:
    """Whether a RUN against this vocabulary has to declare which clone it is about.

    **Read from the DECLARATION, never from a flag or a name.** A vocabulary whose commands are all
    engagement-rooted never mentions the placeholder, so this is False and the whole rule is inert -
    which is what keeps it from being a tax on an install that has no clones to choose between.
    """
    return any(declares_clone(spec) for spec in vocabulary.values())


def clone_name_problem(clone: str) -> str:
    """Why `clone` is not a name a run may declare, or `""` when it is - **a NAME, not a path.**

    It is substituted INTO a declaration, so a value carrying a separator or a `..` chooses the
    directory rather than naming one - and `./alpha/../..` resolves to the ROOT itself, which
    exists, so the two checks that guard a literal `cwd` would wave it through: the command would
    run in the runtime root while the record said a clone. Measured by writing the test for it.
    A dot inside a name is fine (`pvl-rentals.v2`); `.`, `..` and anything path-shaped are not.
    """
    name = str(clone).strip()
    if not name:
        return "empty"
    if name == CLONE_NONE:
        return (f"{CLONE_NONE!r} is the word for a run that touches NO clone, not a clone's name")
    if name in (".", "..") or name != Path(name).name:
        return f"{clone!r} is not a plain directory name"
    return ""


def clone_problem(root: Path, clone: str, vocabulary: dict) -> str:
    """Why `clone` cannot be this run's target, or `""` when it can.

    **Validated rather than trusted, and validated at START rather than at the first call.** It is
    the same three steps `_cwd` takes - the value must be a NAME, `resolve_in_root` refuses an
    escape, the directory has to exist - run once over every declaration that names a clone, so a
    target that cannot resolve is refused before anything has been dispatched rather than halfway
    through a chain.
    """
    bad = clone_name_problem(clone)
    if bad:
        return bad
    for name, spec in sorted(vocabulary.items()):
        if not declares_clone(spec):
            continue
        rel = str(spec.get("cwd") or "")
        try:
            path = resolve_in_root(root, rel.replace(CLONE, clone))
        except ValueError as e:
            return f"`{name}` declares cwd `{rel}`, and {clone!r} makes it: {e}"
        if not path.is_dir():
            return (f"`{name}` declares cwd `{rel}`, which {clone!r} makes "
                    f"`{path.as_posix()}` - not a directory inside the repo")
    return ""


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


def _accepted_args(spec: dict) -> str:
    """The argument kind a declaration accepts, or `""`. At most one, from a closed vocabulary."""
    accepts = str(spec.get("accepts") or "").strip()
    if accepts and accepts not in ARG_KINDS:
        raise ValueError(f"declares an unknown `accepts` {accepts!r}; the vocabulary is "
                         f"{', '.join(ARG_KINDS)}")
    return accepts


def _path_argument(spec: dict, cwd: Path, path: str | None) -> list[str]:
    """The one argument a declared command may take - VALIDATED rather than substituted.

    Returns the single cwd-relative path to append, or `[]` when the command takes none. **Every
    refusal is a `ValueError`**, which `run_command` renders as an ERROR string the way it does for
    `cwd`: a command that cannot do what it was asked says so rather than running something else.

    **`cwd`-relative, not root-relative, and that is the whole point** - the child resolves its
    arguments in its own working directory, so a path valid in the root would name nothing there.
    It is also the base check 47 reads a declared `argv` from, for the same reason.
    """
    accepts = _accepted_args(spec)
    if not accepts:
        if path is not None:
            raise ValueError("this command declares no `accepts`, so it takes no path - a caller "
                             "cannot add an argument to a frozen argv")
        return []
    if path is None or not str(path).strip():
        raise ValueError(f"this command takes one {accepts}, and none was supplied")
    # Confined to the COMMAND'S OWN cwd, so the message names that rather than "the repo root" -
    # `resolve_in_root` reports its own root, and here its root is a directory inside the repo.
    try:
        target = resolve_in_root(cwd, str(path).strip())
    except ValueError:
        raise ValueError(f"path escapes the command's own working directory: {path!r}")
    if not target.is_file():
        raise ValueError(f"path is not a file inside the command's own cwd: {path!r}")
    return [target.relative_to(cwd).as_posix()]


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
                 vocabulary: dict | None = None, human_approval: bool = False,
                 role: str = "", clone: str = ""):
        self.root = Path(root).expanduser().resolve()
        self.spec = copy.deepcopy(spec) if spec else {}
        self.vocabulary = (load_vocabulary(self.root)
                           if vocabulary is None else vocabulary)
        self.human_approval = bool(human_approval)
        # The registry KEY, passed in rather than read out of the spec: the spec's own `role`
        # field is a display name ("Recorder") and the key is the identity every other record
        # uses. It is only ever handed to a child process - see `_execute`.
        self.role = str(role)
        # **THE RUN'S TARGET CLONE - never the model endpoint that `executor.target_for` returns.**
        # It is what a `cwd` of `repos/{clone}` resolves against, and `""` means the run declared
        # none, which is a REFUSAL rather than a default for every command that needs one.
        self.clone = str(clone)

    # --- surface ----------------------------------------------------------
    def granted(self) -> dict:
        """The vocabulary entries this role may actually run."""
        allowed = self.spec.get("exec_allow") or []
        return {str(n): self.vocabulary[str(n)] for n in allowed
                if str(n) in self.vocabulary}

    def tool_schemas(self) -> list[dict]:
        names = sorted(self.granted())
        if not names:
            return []
        props: dict[str, dict] = {
            "command": {"type": "string", "enum": names,
                        "description": "which declared command to run"}}
        # **The argument field is advertised ONLY for the commands that declare one, and their names
        # are in the description** - so the surface never suggests an argument a command would
        # refuse. Supplying one to a command that takes none is refused by `run_command` rather than
        # ignored, because silently dropping it would run something other than what was asked for.
        takes = sorted(n for n in names if (self.granted()[n].get("accepts") or "").strip())
        if takes:
            props["path"] = {
                "type": "string",
                "description": ("a path inside the command's own working directory - accepted by "
                                + ", ".join(takes))}
        return [{"type": "function", "function": {
            "name": TOOL_NAME,
            "description": ("Run one of this repo's declared read/check commands. You "
                            "cannot supply a command or its arguments - only a name. "
                            "Available: " + ", ".join(names)),
            "parameters": {"type": "object", "properties": props,
                           "required": ["command"]}}}]

    def call_tool(self, name: str, args: dict) -> str | None:
        """Run the command tool, or `None` when the name is not this layer's. See `workspace.py`."""
        if name != TOOL_NAME:
            return None
        try:
            return self.run_command(**(args or {}))
        except TypeError as e:
            return f"ERROR: bad args for {name}: {e}"

    # --- execution --------------------------------------------------------
    def run_command(self, command: str, path: str | None = None) -> str:
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

        kind = str(spec.get("kind", "read"))
        if kind not in VALID_KINDS:
            return f"ERROR: {command!r} declares an invalid kind {kind!r}"

        # **`cwd` is resolved BEFORE the argument, because the argument is resolved AGAINST it.** The
        # path a command accepts is cwd-relative for the same reason check 47 reads `argv` from
        # `cwd`: it is the directory the runtime actually resolves in.
        try:
            cwd = self._cwd(spec)
            extra = _path_argument(spec, cwd, path)
        except ValueError as e:
            return f"ERROR: {e}"
        argv = [exe] + declared[1:] + extra

        # Part D: an acting command does not run without a human decision.
        if kind == "act" and self.human_approval:
            return self._await_approval(str(command), spec, declared, argv, cwd, extra)

        return self._execute(str(command), spec, declared, argv, cwd, extra)

    def _cwd(self, spec: dict) -> Path:
        """The command's working directory: repo-relative, confined to the repo.

        **The run's clone, when the declaration names one.** `repos/{clone}` is substituted and then
        resolved through the same steps as any other `cwd` - which is the point: the target is a
        value the RUN supplied, not a string the declaration trusted. The name rule comes first,
        because a path-shaped value can resolve to the root and pass both of the others.

        **A run that declared no clone is refused here rather than defaulted to one.** That is the
        whole difference `T50` was filed for: resolving it from anything else would be a guess about
        which repository to act on, and a guess here prints as a PASS credited to this run.
        """
        rel = str(spec.get("cwd") or ".").strip() or "."
        if CLONE in rel:
            if not self.clone:
                raise ValueError(
                    f"cwd is `{rel}`, which names the RUN's clone, and this run declared none - "
                    f"start it with `--clone <name>`, or with `--clone none` if it never touches a "
                    f"clone at all")
            if self.clone == CLONE_NONE:
                raise ValueError(
                    f"cwd is `{rel}`, which names the RUN's clone, and this run declared "
                    f"`--clone {CLONE_NONE}` - so there is no repository to resolve against. That "
                    f"declaration was legal and this command is what makes it false: name the "
                    f"clone the work is about.")
            bad = clone_name_problem(self.clone)
            if bad:
                raise ValueError(f"this run's clone is {bad}, and cwd `{rel}` substitutes it")
            rel = rel.replace(CLONE, self.clone)
        path = resolve_in_root(self.root, rel)
        if not path.is_dir():
            raise ValueError(f"cwd is not a directory inside the repo: {rel!r}")
        return path

    def _execute(self, command: str, spec: dict, declared: list[str],
                 argv: list[str], cwd: Path, extra: list[str] | None = None) -> str:
        timeout = _bounded_int(spec.get("timeout"), DEFAULT_TIMEOUT, 1, MAX_TIMEOUT)
        # env additions are for THIS child only - never os.environ, never the shell
        env = dict(os.environ)
        # WHO AND WHERE THE CHILD IS, for every command, before the declared overrides below.
        # A command's `argv` is a FROZEN vector with no substitution, so without these two a
        # command cannot answer a question about the run it belongs to - and the one that needs
        # to is the write-policy reader, which would otherwise have to be declared once per role
        # and restate the role list in a second place. `spec.env` below still wins.
        env["SOLAR_ROOT"] = str(self.root)
        env["SOLAR_ROLE"] = self.role
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
        # The target is printed for the same reason `cwd` is: the call record has to name what it
        # actually acted on, and a path-accepting command has a different target every call.
        target = f", path={extra[-1]}" if extra else ""
        lines = [f"[{command}] {verdict} exit {_exit_code(proc.returncode)} "
                 f"in {elapsed:.1f}s (kind={kind}, cwd={shown_cwd}{target})"]
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
                        argv: list[str], cwd: Path, extra: list[str] | None = None) -> str:
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
                return self._execute(command, spec, declared, argv, cwd, extra)
            reason = text.split(":", 1)[1].strip() if ":" in text else "no reason given"
            return (f"DENIED: {reason}\nDo not retry this command. Adapt, or report "
                    f"that it is blocked.")

        proposal = adir / f"{aid}.md"
        if not proposal.is_file():
            proposal.write_text(self._proposal(command, spec, declared, cwd, aid, extra),
                                encoding="utf-8")
        return (f"AWAITING APPROVAL {aid}\n"
                f"An acting command does not run without a human decision. A human must "
                f"write 'allow' or 'deny: <reason>' to .solar/approvals/{aid}.decision. "
                f"You cannot proceed and retrying will not help - report that you are "
                f"waiting on approval.")

    def _proposal(self, command: str, spec: dict, declared: list[str],
                  cwd: Path, aid: str, extra: list[str] | None = None) -> str:
        try:
            shown_cwd = str(cwd.relative_to(self.root)) or "."
        except ValueError:
            shown_cwd = "."
        # The declared argv plus anything appended for THIS call, because a human approving a
        # command approves the call - and a path-bearing call is a different call each time.
        shown_argv = " ".join([*declared, *(extra or [])])
        return (
            f"# Command approval requested - {command}\n\n"
            f"| field | value |\n| :--- | :--- |\n"
            f"| id | `{aid}` |\n"
            f"| command | `{command}` |\n"
            f"| argv | `{shown_argv}` |\n"
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
