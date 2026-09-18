"""Model executor (v5 §3/§6): provider-neutral in-graph LLM node.

Provider config is read from the ENVIRONMENT at runtime (never stored in
.solar/config.json, never committed):

    SOLAR_API_KEY   (fallback: DEEPSEEK_API_KEY)
    SOLAR_BASE_URL  (default https://api.deepseek.com)
    SOLAR_MODEL     (fallback: cfg.model, fallback "deepseek-chat")

Speaks OpenAI-compatible /chat/completions, so any OpenAI-compatible provider
(DeepSeek, OpenRouter, a local vLLM/Ollama gateway, etc.) works by changing the
env vars. The registry role's `system` prompt is the system message; the task
objective is the user message; repo-bounded workspace functions are offered as
tools. Returns {output, usage, tool_calls, error}.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlparse

from .commands import CommandRunner
from .core import read_text
from .workspace import Workspace

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"

# Tier -> concrete id, per provider family (v5.6.0). Repos declare a TIER, so a provider
# rename is ONE edit here instead of one edit per repo per file. That duplication is how a
# single non-existent id (`deepseek-v4-flash`) came to sit in one config unreviewed.
#
# Keyed by a substring of the base-url host. A family we do not know cannot have its tiers
# resolved, and that is reported rather than guessed.
MODEL_TIERS: dict[str, dict[str, str]] = {
    "deepseek": {
        "fast": "deepseek-flash",
        "reasoner": "deepseek-v4-pro",
        "alias": "deepseek-chat",
    },
}
# model round-trips per specialist node; configurable via SOLAR_MAX_ROUNDS
# (complex read-heavy roles like investigator/code-reviewer exceed a low cap)
MAX_TOOL_ROUNDS = int(os.environ.get("SOLAR_MAX_ROUNDS", "12"))
# Sampling temperature for specialist calls. The loop used to send none and so
# inherited the provider default, which made tool-use convergence a coin flip:
# identical role + objective + model finished in 5 rounds on one run and burned
# the entire budget on the next. "default" omits the field entirely, for
# OpenAI-compatible gateways that reject it.
DEFAULT_TEMPERATURE = "0.2"
# tool rounds remaining from which the model is told it is running out
NUDGE_ROUNDS_LEFT = 1
# the last round is called with NO tools offered, so it has to return text
FINAL_ROUND_INSTRUCTION = (
    "Tool budget exhausted: there are no tool rounds left. Answer now, in plain "
    "text, from the evidence already gathered. Cite what you established and "
    "write 'not verified' for anything you did not get to establish. Do not guess "
    "and do not request another tool call - none is available.")


def tool_output_chars() -> int:
    """Cap on characters of a single tool result kept in context (0 = unlimited).

    Read-heavy roles balloon context because full-file reads accumulate across
    rounds; truncating each result bounds per-round growth. Tunable via
    SOLAR_TOOL_OUTPUT_CHARS (default 8000 — proven 100% pass at lower cost on
    the eval battery; raise for cases that legitimately need >8k-char reads)."""
    try:
        return int(os.environ.get("SOLAR_TOOL_OUTPUT_CHARS", "8000"))
    except ValueError:
        return 8000


def _cap_tool(text: str) -> str:
    cap = tool_output_chars()
    if cap > 0 and text and len(text) > cap:
        return text[:cap] + f"\n…[truncated {len(text)} chars to {cap} " \
                            f"by SOLAR_TOOL_OUTPUT_CHARS]"
    return text


def temperature() -> float | None:
    """Sampling temperature for a specialist call (None = omit the parameter).

    Read per call, not at import, so a run can be reproduced without restarting
    anything. An unparseable or out-of-range value falls back to the default
    rather than failing the run.
    """
    raw = (os.environ.get("SOLAR_TEMPERATURE", DEFAULT_TEMPERATURE) or "").strip()
    if raw.lower() in ("", "default", "none", "off"):
        return None
    try:
        value = float(raw)
    except ValueError:
        return float(DEFAULT_TEMPERATURE)
    return value if 0.0 <= value <= 2.0 else float(DEFAULT_TEMPERATURE)


def _budget_notice(rounds_left: int) -> str:
    """Tell the model how much tool budget is left, and what to do about it.

    The loop previously had no termination pressure of any kind: a model that
    kept finding one more file to read could spend every round and return
    nothing at all. Naming the remaining budget, and the 'not verified' escape,
    is what lets it stop without pretending to know something it does not.
    """
    return (f"Budget notice: {rounds_left} tool round(s) left after this one. "
            f"If the evidence you already have answers the objective, answer now "
            f"in plain text with no tool call. If a fact cannot be established "
            f"with the tools you have, write 'not verified' for it and answer "
            f"anyway.")


def api_key() -> str | None:
    return os.environ.get("SOLAR_API_KEY") or os.environ.get("DEEPSEEK_API_KEY") or None


def base_url() -> str:
    return os.environ.get("SOLAR_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def provider_family() -> str:
    """Which model family the configured endpoint speaks ("" when unknown)."""
    host = (urlparse(base_url()).hostname or "").lower()
    for family in MODEL_TIERS:
        if family in host:
            return family
    return ""


def resolve_tier(tier: str) -> str:
    """The concrete id for a tier. Raises when it cannot be answered honestly.

    An unknown tier, or a tier asked of an unknown provider, is a configuration error:
    falling through to a default would run a different model than the one asked for,
    the same class of defect as a failed check reading as a pass.
    """
    family = provider_family()
    if not family:
        raise ValueError(
            f"cannot resolve model tier {tier!r}: no known provider family for "
            f"{base_url()!r} (set an explicit model id, or add the family to MODEL_TIERS)")
    table = MODEL_TIERS[family]
    if tier not in table:
        raise ValueError(f"unknown model tier {tier!r} for {family} "
                         f"(have: {', '.join(sorted(table))})")
    return table[tier]


def resolve_model(cfg_model: str = "", role_model: str = "", cfg_tier: str = "",
                  role_tier: str = "") -> tuple[str, str]:
    """Resolve the model id for one call, and say which level supplied it.

    Precedence (TD-5.4-1, extended v5.6.0): `SOLAR_MODEL` > role `model` > role
    `model_tier` > `cfg.model` > `cfg.model_tier` > the built-in default. An explicit
    id beats a tier **at the same level**, and a nearer level beats a further one - so
    a per-run override stays absolute, and one chain can still mix tiers.

    Returns (id, source) because `doctor` has to SHOW the provenance: knowing the id is
    not enough to tell a deliberate env override from a stale config pin. One ladder,
    one place - a second copy would drift.
    """
    ladder = (("env SOLAR_MODEL", "id", os.environ.get("SOLAR_MODEL") or ""),
              ("role model", "id", role_model or ""),
              ("role model_tier", "tier", role_tier or ""),
              ("config model", "id", cfg_model or ""),
              ("config model_tier", "tier", cfg_tier or ""))
    for source, kind, value in ladder:
        value = value.strip()
        if not value:
            continue
        if kind == "id":
            return value, source
        return resolve_tier(value), f"{source}={value}"
    return DEFAULT_MODEL, "default"


def model_name(cfg_model: str = "", role_model: str = "") -> str:
    """The resolved model id (see `resolve_model`)."""
    return resolve_model(cfg_model, role_model)[0]


def reasoning_effort(cfg_effort: str = "", role_effort: str = "") -> str:
    """Reasoning / thinking effort for one call ("" = send no such field).

    Ladder mirrors the model ladder (TD-5.4-2): `SOLAR_REASONING_EFFORT` env > the
    ROLE's registry `reasoning` > `cfg.reasoning_effort`.

    Deliberately unvalidated and OFF by default. Providers disagree about the
    accepted scale and about whether they accept the field at all, so a bad value
    has to come back as the provider's own error rather than being silently dropped
    here. Nothing is sent unless some level supplies a value, so this cannot change
    the behaviour of an existing repo.
    """
    return (os.environ.get("SOLAR_REASONING_EFFORT") or role_effort or cfg_effort
            or "").strip()


# Ids a provider serves through an alias it does not list in /models. DeepSeek
# accepts `deepseek-chat` while `GET /models` returns only `deepseek-flash` and
# `deepseek-v4-pro`, so absence from that list is not proof of a bad id.
UNLISTED_ALIASES = ("deepseek-chat",)


def known_models(timeout: float = 15.0) -> tuple[list[str] | None, str]:
    """Ask the provider which model ids it serves: (ids|None, error).

    `doctor`-only. A mis-set id is otherwise invisible until the first chat call
    comes back 400 - which is how a non-existent `deepseek-v4-flash` pin sat in a
    repo config unnoticed. Never raises: doctor reports, it does not fail a run.
    """
    key = api_key()
    if key is None:
        return None, "no API key"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key, base_url=base_url(), timeout=timeout)
        return [m.id for m in client.models.list().data], ""
    except Exception as e:  # network, auth, or SDK failure
        return None, str(e)


def available() -> bool:
    """True when a real model call is possible (an API key is present)."""
    return api_key() is not None


# The three runners (v5 §3): agent-dispatch hands off to the repo's .agent.md
# agents in the IDE; http calls an OpenAI-compatible endpoint; stub is
# deterministic and offline. Kept here so the CLI can offer them as choices.
RUNNERS = ("agent-dispatch", "http", "stub")


def select_runner(cfg_runner: str = "") -> str:
    """Resolve which runner executes specialist work (v5 §3, provider-agnostic).

    Ladder: `SOLAR_RUNNER` (env, or `run --runner`, which sets it for the run) >
    the repo's `config.json` `runner` > auto (http when a key is set, else stub).

    The env level beating the config is the point (TD-5.4-9). A repo that pins
    `agent-dispatch` can be exercised through `http` for one run **without
    editing its config**, which is what the v5.4.1 integration test had to do —
    editing a live engagement's `.solar/config.json` and restoring it, twice.
    Before this the config always won, so `SOLAR_RUNNER` could never be reached:
    the opposite of `SOLAR_MODEL`, where env beats both role and config.

    An unrecognised value **raises** rather than falling through to auto. A typo
    that silently selects a different runner than the caller asked for is the
    same class of defect as a failed check reading as a pass.
    """
    for source, value in (("SOLAR_RUNNER", os.environ.get("SOLAR_RUNNER", "")),
                          ("config runner", cfg_runner)):
        value = (value or "").strip()
        if not value:
            continue
        if value in RUNNERS:
            return value
        raise ValueError(f"unknown runner {value!r} from {source} "
                         f"(expected one of: {', '.join(RUNNERS)})")
    return "http" if available() else "stub"


def write_handoff(role: str, system_prompt: str, objective: str, repo: Path,
                  cfg_model: str = "", attempt: int = 1, chain_note: str = "",
                  role_model: str = "") -> Path:
    """AgentDispatchRunner: write a task handoff for one .agent.md specialist.

    Returns the handoff markdown path (under <repo>/.solar/handoffs/). The human
    runs the matching agent in VS Code Copilot (DeepSeek via the extension) and
    pastes the result back (or saves it to <handoff>.result.md) to resume.

    `chain_note` (optional): when the dispatch is part of a named chain, a short
    block giving the chain name/text + the driver-model rule (you are ONE link;
    the coordinator runs the rest). Never instructs self-running.
    """
    import hashlib
    from datetime import datetime
    hdir = Path(repo) / ".solar" / "handoffs"
    hdir.mkdir(parents=True, exist_ok=True)
    # deterministic name per (role, attempt, objective) so a resume overwrites
    # the same file instead of spawning duplicates
    slug = hashlib.md5((objective or "").encode("utf-8")).hexdigest()[:6]
    path = hdir / f"{role}-attempt{attempt}-{slug}.md"
    model_hint = model_name(cfg_model, role_model)
    body = (f"# SOLAR handoff — specialist: {role}\n\n"
            f"_model routing: {model_hint} (via IDE agent) · generated "
            f"{datetime.now().isoformat(timespec='seconds')} · attempt {attempt}_\n\n"
            f"## Objective\n\n{objective}\n\n"
            f"## System prompt (registry)\n\n```\n{system_prompt}\n```\n\n")
    if chain_note:
        body += (f"## Chain context\n\n{chain_note}\n\n"
                 f"You are ONE link of this chain. The coordinator (Governor driver "
                 f"/ `--auto`) runs the other links in order and threads context; "
                 f"you do NOT run or spawn other specialists yourself — nested agents "
                 f"lack the agent-spawn tool, and one agent composing the whole "
                 f"chain is the exact failure the harness prevents. Return your "
                 f"step's deliverable; the coordinator continues the chain.\n\n")
    body += (f"## How to run\n\n"
             f"1. Open this repo in VS Code Copilot (agent mode).\n"
             f"2. Run the `{role}` specialist agent (`.github/agents/{role}.agent.md`)\n"
             f"   — its model is DeepSeek via the DeepSeek-for-Copilot extension.\n"
             f"3. Give it the Objective above; it uses its own tools (read/edit/exec).\n"
             f"4. Paste the agent's final result into the CLI when prompted, or save\n"
             f"   it to `{path}.result.md` and type that path.\n\n"
             f"## Notes\n\n- The graph (this run) adds routing + gates + checkpoint "
             f"around the agent; the agent does the real work.\n"
             f"- Result is recorded in the run-card and ledger, not the handoff.\n")
    path.write_text(body, encoding="utf-8")
    return path


def resolve_result(value: str, repo: Path) -> str:
    """Turn a resumed value into specialist output text.

    If the value points to an existing file (e.g. the agent's .result.md), read
    and return its contents; otherwise treat the value itself as the result.
    """
    value = (value or "").strip()
    if not value:
        return "(no agent result provided)"
    p = Path(value)
    if not p.is_absolute():
        p = Path(repo) / value
    if p.is_file():
        try:
            # utf-8-sig: this file is usually written by an IDE agent or a human, and a
            # BOM would otherwise arrive as the first character of the specialist output.
            return read_text(p)
        except OSError:
            pass
    return value


class _ToolLayer:
    """One dispatch surface over the repo tool layers (workspace + commands).

    Each layer advertises only what the ROLE may use, so a layer that grants nothing
    returns no schemas and never sees a call. `run_command` therefore does not exist
    for a role without `exec_allow`, exactly as `write_file` does not exist for a
    read-only role - a tool that is not offered cannot be argued into use.
    """

    def __init__(self, *layers):
        self.layers = layers

    def tool_schemas(self) -> list[dict]:
        return [schema for layer in self.layers for schema in layer.tool_schemas()]

    def call_tool(self, name: str, args: dict) -> str:
        for layer in self.layers:
            if layer.handles(name):
                return layer.call_tool(name, args)
        return f"ERROR: unknown tool {name}"


class ExecutorResult(dict):
    """Thin dict: output / usage(in,out) / tool_calls / error / model / forced_final."""


def _tool_loop(client, model: str, messages: list[dict], ws, max_rounds: int,
               effort: str = "") -> ExecutorResult:
    """Run the model/tool loop for one specialist node.

    Three termination rules, each added because the loop was measured returning
    NO answer at all 4 runs in 5 on a real read-only role over a one-file,
    one-fact objective:

      * an explicit temperature (an inherited provider default made convergence
        non-deterministic on identical inputs);
      * a budget notice once the tool rounds nearly run out;
      * a FINAL round called with no tools offered at all, so the response has to
        be text. A node that cannot finish now hands back what it did establish,
        with the gaps named, instead of failing the run outright.

    `forced_final` marks an answer produced by that last, tool-less round, so a
    reader can tell "answered" from "cut off, and answered anyway".
    """
    rounds = max(1, max_rounds)
    temp = temperature()
    tools = ws.tool_schemas()
    total_in = total_out = tool_calls = 0

    def _result(output: str, err: str | None, forced: bool) -> ExecutorResult:
        return ExecutorResult(output=output, usage={"in": total_in, "out": total_out},
                              tool_calls=tool_calls, error=err, model=model,
                              forced_final=forced)

    for rnd in range(1, rounds + 1):
        final_round = rnd == rounds
        if final_round:
            messages.append({"role": "user", "content": FINAL_ROUND_INSTRUCTION})
        elif rounds - rnd <= NUDGE_ROUNDS_LEFT:
            messages.append({"role": "user", "content": _budget_notice(rounds - rnd)})
        payload: dict = {"model": model, "messages": messages}
        if temp is not None:
            payload["temperature"] = temp
        if effort:
            payload["reasoning_effort"] = effort
        if not final_round:
            payload["tools"] = tools
        try:
            resp = client.chat.completions.create(**payload)
            if getattr(resp, "usage", None):
                total_in += resp.usage.prompt_tokens or 0
                total_out += resp.usage.completion_tokens or 0
            msg = resp.choices[0].message
            text = (msg.content or "").strip()
            calls = list(getattr(msg, "tool_calls", None) or [])
        except Exception as e:  # provider/network failure
            return _result(f"ERROR calling model ({model}): {e}", str(e), False)
        # A tool-less final round must answer; so must any round that chose to
        # answer without tools. Text wins over a stray call in both cases.
        if final_round or not calls:
            if text:
                return _result(msg.content, None, final_round)
            return _result("ERROR: model returned no answer text", "empty_output",
                           final_round)
        messages.append({"role": "assistant", "content": msg.content or "",
                         "tool_calls": [{"id": tc.id, "type": "function",
                                          "function": {"name": tc.function.name,
                                                       "arguments": tc.function.arguments}}
                                         for tc in calls]})
        for tc in calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            tool_calls += 1
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": _cap_tool(ws.call_tool(tc.function.name, args))})
    # Unreachable: the final round always returns above. Defensive only, and it
    # keeps the old error id so anything keyed on it still recognises the case.
    return _result("ERROR: reached max tool rounds without a final answer",
                   "max_rounds", False)


def stub_result(role: str, objective: str, why: str) -> ExecutorResult:
    """The deterministic, offline result — and WHICH reason produced it (TD-5.6-7).

    `why` is not decoration. "No key is set" and "the caller asked for the stub" are
    different facts about the run, and a reader (or a run-card) that cannot tell them
    apart cannot tell a fallback from a deliberate choice. It is also the only signal
    that an offline run was intended rather than degraded into.
    """
    return ExecutorResult(
        output=(f"[{role}] STUB ({why}) — plan for: {objective}\n"
                f"  - PREMISE_GATE: verify the request vs ground truth\n"
                f"  - read the relevant files (workspace tool)\n"
                f"  - implement the minimal change\n"
                f"  - self-check + tests"),
        usage={"in": 0, "out": 0}, tool_calls=0, error=None, model="stub")


def run(role: str, system_prompt: str, objective: str, repo: Path,
        cfg_model: str = "", max_rounds: int = MAX_TOOL_ROUNDS,
        spec: dict | None = None, human_approval: bool = False,
        cfg_reasoning: str = "", cfg_tier: str = "", runner: str = "") -> ExecutorResult:
    """Run one specialist node: system prompt + objective, with workspace tools.

    `spec` is the role's registry entry (v5 §6). It is handed to the tool layers so
    policy derives from the ROLE, not the process: which tools are offered, where the
    role may write, and which commands it may run. Its `model` is the per-node model
    override (TD-5.4-1) and its `reasoning` the per-node effort (TD-5.4-2).
    `human_approval` reaches the command layer's approval gate.

    `runner` is the ALREADY-RESOLVED runner from `select_runner` (TD-5.6-7). It is
    passed in rather than re-resolved here because one ladder must have one outcome:
    this function previously decided on the api key alone, so `run --runner stub` with
    a key in the environment made a real, billable HTTP call — the exact opposite of
    what reaching for the stub is for.

    Falls back to a stub (no network) when no API key is present, so the graph
    stays runnable/testable without credentials.
    """
    if runner == "stub":
        return stub_result(role, objective, "runner=stub, by request")
    key = api_key()
    if key is None:
        return stub_result(role, objective, "no SOLAR_API_KEY set")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key, base_url=base_url())
    except Exception as e:  # pragma: no cover - import/init failure
        return ExecutorResult(output=f"ERROR initializing client: {e}",
                              usage={"in": 0, "out": 0}, tool_calls=0, error=str(e),
                              model=model_name(cfg_model))
    try:
        model, _source = resolve_model(cfg_model=cfg_model,
                                       role_model=(spec or {}).get("model", ""),
                                       cfg_tier=cfg_tier,
                                       role_tier=(spec or {}).get("model_tier", ""))
    except ValueError as e:
        # An unresolvable tier is a configuration error, and the honest place for it is
        # the executor's error path: the review node then REJECTS the run instead of
        # approving output produced with a model nobody asked for.
        return ExecutorResult(output=f"ERROR: {e}", usage={"in": 0, "out": 0},
                              tool_calls=0, error=str(e), model="unresolved")
    ws = _ToolLayer(Workspace(repo, spec),
                    CommandRunner(repo, spec, human_approval=human_approval))
    messages: list[dict] = [
        {"role": "system",
         "content": (system_prompt or f"You are the {role} specialist.")
                    + f"\n\nRepo root: {repo}\n"
                      "Use the provided tools to inspect the repo before answering. "
                      "When you have the answer, reply with plain text (markdown ok) — "
                      "no tool call needed."},
        {"role": "user", "content": objective},
    ]
    effort = reasoning_effort(cfg_reasoning, (spec or {}).get("reasoning", ""))
    return _tool_loop(client, model, messages, ws, max_rounds, effort)
