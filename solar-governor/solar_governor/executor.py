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

import os
from pathlib import Path

from .workspace import Workspace

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
# model round-trips per specialist node; configurable via SOLAR_MAX_ROUNDS
# (complex read-heavy roles like investigator/code-reviewer exceed a low cap)
MAX_TOOL_ROUNDS = int(os.environ.get("SOLAR_MAX_ROUNDS", "12"))


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


def api_key() -> str | None:
    return os.environ.get("SOLAR_API_KEY") or os.environ.get("DEEPSEEK_API_KEY") or None


def base_url() -> str:
    return os.environ.get("SOLAR_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def model_name(cfg_model: str = "") -> str:
    return os.environ.get("SOLAR_MODEL") or cfg_model or DEFAULT_MODEL


def available() -> bool:
    """True when a real model call is possible (an API key is present)."""
    return api_key() is not None


def select_runner(cfg_runner: str = "") -> str:
    """Resolve which runner executes specialist work (v5 §3, provider-agnostic).

    Order: explicit config/env > auto (http when a key is set, else stub).
    Values: "agent-dispatch" (hand off to the repo's .agent.md agents in the
    IDE) · "http" (OpenAI-compatible) · "stub" (deterministic, offline).
    """
    r = cfg_runner or os.environ.get("SOLAR_RUNNER", "")
    if r in ("agent-dispatch", "http", "stub"):
        return r
    return "http" if available() else "stub"


def write_handoff(role: str, system_prompt: str, objective: str, repo: Path,
                  cfg_model: str = "", attempt: int = 1, chain_note: str = "") -> Path:
    """AgentDispatchRunner: write a task handoff for one .agent.md specialist.

    Returns the handoff markdown path (under <repo>/.solar/handoffs/). The human
    runs the matching agent in VS Code Copilot (DeepSeek via the extension) and
    pastes the result back (or saves it to <handoff>.result.md) to resume.

    `chain_note` (optional): when the dispatch is a named chain, a short
    instruction block telling this agent it is the chain ENTRY and to run the
    whole chain itself (see .github/instructions/solar-agent-chain.md).
    """
    import hashlib
    from datetime import datetime
    hdir = Path(repo) / ".solar" / "handoffs"
    hdir.mkdir(parents=True, exist_ok=True)
    # deterministic name per (role, attempt, objective) so a resume overwrites
    # the same file instead of spawning duplicates
    slug = hashlib.md5((objective or "").encode("utf-8")).hexdigest()[:6]
    path = hdir / f"{role}-attempt{attempt}-{slug}.md"
    model_hint = model_name(cfg_model)
    body = (f"# SOLAR handoff — specialist: {role}\n\n"
            f"_model routing: {model_hint} (via IDE agent) · generated "
            f"{datetime.now().isoformat(timespec='seconds')} · attempt {attempt}_\n\n"
            f"## Objective\n\n{objective}\n\n"
            f"## System prompt (registry)\n\n```\n{system_prompt}\n```\n\n")
    if chain_note:
        body += (f"## Chain mode\n\n{chain_note}\n\n"
                 f"You are the CHAIN ENTRY. After your own step, run the next "
                 f"specialist(s) yourself per the shared "
                 f"`solar-agent-chain.instructions.md`; the LAST specialist returns "
                 f"the FINAL result, which you return as your result. Do not return "
                 f"after your own step alone.\n\n")
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
            return p.read_text(encoding="utf-8")
        except OSError:
            pass
    return value


class ExecutorResult(dict):
    """Thin dict: output / usage(in,out) / tool_calls / error / model."""


def run(role: str, system_prompt: str, objective: str, repo: Path,
        cfg_model: str = "", max_rounds: int = MAX_TOOL_ROUNDS) -> ExecutorResult:
    """Run one specialist node: system prompt + objective, with workspace tools.

    Falls back to a stub (no network) when no API key is present, so the graph
    stays runnable/testable without credentials.
    """
    key = api_key()
    if key is None:
        return ExecutorResult(
            output=(f"[{role}] STUB (no SOLAR_API_KEY set) — plan for: {objective}\n"
                    f"  - PREMISE_GATE: verify the request vs ground truth\n"
                    f"  - read the relevant files (workspace tool)\n"
                    f"  - implement the minimal change\n"
                    f"  - self-check + tests"),
            usage={"in": 0, "out": 0}, tool_calls=0, error=None, model="stub")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key, base_url=base_url())
    except Exception as e:  # pragma: no cover - import/init failure
        return ExecutorResult(output=f"ERROR initializing client: {e}",
                              usage={"in": 0, "out": 0}, tool_calls=0, error=str(e),
                              model=model_name(cfg_model))
    model = model_name(cfg_model)
    ws = Workspace(repo)
    messages: list[dict] = [
        {"role": "system",
         "content": (system_prompt or f"You are the {role} specialist.")
                    + f"\n\nRepo root: {repo}\n"
                      "Use the provided tools to inspect the repo before answering. "
                      "When you have the answer, reply with plain text (markdown ok) — "
                      "no tool call needed."},
        {"role": "user", "content": objective},
    ]
    total_in = total_out = 0
    tool_calls = 0
    error = None
    try:
        for _ in range(max_rounds):
            resp = client.chat.completions.create(
                model=model, messages=messages, tools=ws.tool_schemas())
            if getattr(resp, "usage", None):
                total_in += resp.usage.prompt_tokens or 0
                total_out += resp.usage.completion_tokens or 0
            msg = resp.choices[0].message
            if msg.tool_calls:
                messages.append({"role": "assistant",
                                 "content": msg.content or "", "tool_calls": [
                                     {"id": tc.id, "type": "function",
                                      "function": {"name": tc.function.name,
                                                   "arguments": tc.function.arguments}}
                                     for tc in msg.tool_calls]})
                for tc in msg.tool_calls:
                    import json as _json
                    try:
                        args = _json.loads(tc.function.arguments or "{}")
                    except Exception:
                        args = {}
                    tool_calls += 1
                    result = ws.call_tool(tc.function.name, args)
                    messages.append({"role": "tool", "tool_call_id": tc.id,
                                     "content": _cap_tool(result)})
                continue
            return ExecutorResult(output=msg.content or "(no output)",
                                  usage={"in": total_in, "out": total_out},
                                  tool_calls=tool_calls, error=None, model=model)
        return ExecutorResult(output="ERROR: reached max tool rounds without a final answer",
                              usage={"in": total_in, "out": total_out},
                              tool_calls=tool_calls, error="max_rounds", model=model)
    except Exception as e:
        error = str(e)
        return ExecutorResult(output=f"ERROR calling model ({model}): {error}",
                              usage={"in": total_in, "out": total_out},
                              tool_calls=tool_calls, error=error, model=model)
