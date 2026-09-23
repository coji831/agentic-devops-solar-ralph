"""Ledger (v5 §12): the running record of runs — appended, never rewritten.

§12 says the checkpoint is the source and the ledger is the human view. What the code
did was REPLACE the file on every run, which made it a view of the *last* run and
silently destroyed anything else at that path. That is not a theoretical risk: it
destroyed a 115-line hand-written task brief in a real engagement (2026-09-19).

So the rule is now mechanical rather than a matter of care:

* **One section per run**, keyed by thread. Re-recording the same thread updates ITS OWN
  section — a run that steps three times still leaves one section — and touches nothing
  else.
* **Content the runtime did not write is never modified.** Every runtime section is
  wrapped in its own begin/end markers, so prose before, between or *after* sections is
  preserved exactly.
* **Nothing is ever deleted.** The file grows by one section per run. `.solar/runs/`
  holds the same runs as structured cards, and the run-card carries the decisions AND the
  answer, so the structured record is complete on its own. (v5.7.3 — before that the card
  carried the decisions and no answer, so the sentence was true of the process and false
  of the result; TD-5.7-6. This section is the human view and stays short: a reader who
  wants what the run concluded follows the thread id into the card.)

This makes "the ledger is the record" true, which §12 and the install block both already
claimed. A derived view that overwrites itself is a poor record; a log that cannot be
destroyed is a good one.
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

from .core import Config

BEGIN = "<!-- solar-governor run"
END = "<!-- /solar-governor run -->"
HEADER = (
    "<!-- solar-governor ledger — one section per run, marked by the lines above and "
    "below. The runtime updates only its OWN sections (matched by run/thread id) and "
    "never rewrites anything else in this file, so hand-written content here is safe. "
    "The same runs also exist as structured cards in .solar/runs/. -->"
)


def _is_marker(line: str) -> bool:
    return line.strip().startswith(BEGIN)


def _thread_of(line: str) -> str:
    """The thread id a begin-marker names ('' when it names none)."""
    stripped = line.strip()
    remainder = stripped[len(BEGIN):] if stripped.startswith(BEGIN) else stripped
    return remainder.split("|", 1)[0].strip()


def _marker_line(thread: str, state: dict) -> str:
    stamp = _dt.datetime.now().isoformat(timespec="seconds")
    return (f"{BEGIN} {thread} | {stamp} | {state.get('stage', '')} | "
            f"{state.get('verdict') or '-'} -->")


def _section(thread: str, state: dict) -> str:
    lines = [_marker_line(thread, state), "",
             "## Objective", "", state.get("objective", ""), "",
             "## Work Queue", "",
             "| id | task | role | status | stage |",
             "| --- | --- | --- | --- | --- |"]
    for row in state.get("work_queue", []):
        lines.append(f"| {row.get('id','')} | {row.get('task','')[:50]} | "
                     f"{row.get('role','')} | {row.get('status','')} | {row.get('stage','')} |")
    lines += ["", "## Decisions Log", ""]
    for entry in state.get("decisions_log", []):
        lines.append(f"- {entry}")
    lines += ["", f"_stage: {state.get('stage','')} · verdict: {state.get('verdict','-')} · "
                  f"attempts: {state.get('attempts',0)} · model: {state.get('model','-')} · "
                  f"endpoint: {state.get('provider','-') or '-'} · "
                  f"thread: {thread}_", "", END]
    return "\n".join(lines)


def tokenize(text: str) -> list[tuple]:
    """Split a ledger into ordered text/section tokens.

    The split IS the safety property, so it is public and asserted on: text outside a
    begin/end pair survives a re-record untouched, wherever it sits.
    """
    tokens: list[tuple] = []
    buf: list[str] = []
    inside: str | None = None
    for line in text.splitlines(keepends=True):
        if inside is None and _is_marker(line):
            if buf:
                tokens.append(("text", "".join(buf)))
                buf = []
            inside = _thread_of(line)
            buf = [line]
            continue
        buf.append(line)
        if inside is not None and line.strip() == END:
            tokens.append(("section", inside, "".join(buf)))
            inside, buf = None, []
    if buf:
        # an unterminated section is kept as text, so nothing can be lost to it
        tokens.append(("text", "".join(buf)))
    return tokens


def render(tokens: list[tuple]) -> str:
    """Tokens back to file text, normalised so a re-write is byte-identical."""
    blocks: list[str] = []
    for token in tokens:
        body = (token[2] if token[0] == "section" else token[1]).strip("\n")
        if body:
            blocks.append(body)
    return "\n\n".join(blocks) + "\n" if blocks else ""


def record(cfg: Config, state: dict, thread: str = "") -> tuple[Path, str]:
    """Write this run's section. Returns (path, action).

    `action` is "created" (new ledger), "appended" (a new run) or "updated" (this run
    stepping again) — "updated" is what keeps one run to one section instead of leaving
    a trail of half-finished ones.
    """
    path = cfg.ledger_path
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = path.read_text(encoding="utf-8") if path.is_file() else ""
    key = thread or "-"
    section = _section(key, state)

    # **BOTH WRITES PASS `newline="\n"`, AND IT IS NOT COSMETIC (`T57`).** Without it
    # `Path.write_text` translates every `\n` to `\r\n` on Windows, so the file written here is one
    # this module cannot reproduce: `render` emits `\n` between blocks while the section text it read
    # back carries `\r\n`, and the mixed result is a different string. Measured 2026-09-23 - a real
    # `.solar/ledger.md` of 79,717 B fails its own round trip, and a two-record ledger renders 936 B
    # from a file of 939 B. **`render`'s docstring already promises "normalised so a re-write is
    # byte-identical"; this is the line that makes the promise true on the platform it runs on.**
    #
    # **And `git status` cannot see it**, because `core.autocrlf=true` here normalises the diff -
    # which is why a CRLF ledger can sit in a tracked file and read as clean.
    #
    # **Compare BYTES when checking this, never `read_text()`.** Python's universal-newline mode
    # translates CRLF back to `\n` on read, so a text-mode comparison reports the defect as ABSENT;
    # both directions were measured, and the text-mode one lies.
    if not previous.strip():
        path.write_text(f"{HEADER}\n\n{section}\n", encoding="utf-8", newline="\n")
        return path, "created"

    tokens = tokenize(previous)
    action = "appended"
    for index, token in enumerate(tokens):
        if token[0] == "section" and token[1] == key:
            tokens[index] = ("section", key, section)
            action = "updated"
            break
    else:
        tokens.append(("section", key, section))

    path.write_text(render(tokens), encoding="utf-8", newline="\n")
    return path, action

