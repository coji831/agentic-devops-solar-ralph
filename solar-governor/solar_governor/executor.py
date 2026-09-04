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
MAX_TOOL_ROUNDS = 6


def api_key() -> str | None:
    return os.environ.get("SOLAR_API_KEY") or os.environ.get("DEEPSEEK_API_KEY") or None


def base_url() -> str:
    return os.environ.get("SOLAR_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def model_name(cfg_model: str = "") -> str:
    return os.environ.get("SOLAR_MODEL") or cfg_model or DEFAULT_MODEL


def available() -> bool:
    """True when a real model call is possible (an API key is present)."""
    return api_key() is not None


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
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
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
