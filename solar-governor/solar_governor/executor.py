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


def round_budget(spec: dict | None = None) -> int:
    """How many round-trips THIS ROLE gets. The precedence is the whole function.

    An explicit `SOLAR_MAX_ROUNDS` wins, because the wrapper's `--max-rounds` is documented as
    "the record" - a role able to veto it would make the flag a suggestion. Absent one, the role's
    own `max_rounds` in the registry decides, beside the `reasoning` key this module already reads
    from a spec. Absent both, `MAX_TOOL_ROUNDS`.

    A role declares its own budget because the budget is a property of what the role DOES:
    measured 2026-09-25, a `recorder` cut off at 12 rounds came back REJECTED twice while the same
    work at 24 finished on its own terms - and the cut-off run cost MORE, so the low cap bought
    nothing. See row H in `Promyro/context/solar-evaluation/`.
    """
    explicit = os.environ.get("SOLAR_MAX_ROUNDS", "").strip()
    if explicit.isdigit():
        return max(1, int(explicit))
    return max(1, int((spec or {}).get("max_rounds") or MAX_TOOL_ROUNDS))


# Sampling temperature for specialist calls. The loop used to send none and so
# inherited the provider default, which made tool-use convergence a coin flip:
# identical role + objective + model finished in 5 rounds on one run and burned
# the entire budget on the next. "default" omits the field entirely, for
# OpenAI-compatible gateways that reject it.
DEFAULT_TEMPERATURE = "0.2"
# tool rounds remaining from which the model is told it is running out
NUDGE_ROUNDS_LEFT = 1
# **The tool-call TRANSCRIPT (T10, 2026-09-23) - and it records a SHAPE, not the payload.**
#
# What could not be answered without it: `audit-run.py`'s own NOT ESTABLISHED line - *"did the link
# that reported an edit actually call a write tool?"* - because `tool_calls` in the state DB is ONE
# INTEGER per run (measured 2026-09-22: 56 writes, 1 byte each, summing to 808), while the calls
# themselves lived in `_tool_loop`'s local `messages` list and were discarded when the link ended.
#
# **Why the arguments and results are not stored, and why the head is 200 chars.** All three uses -
# which tool acted on what, how big each result was, and how many calls were REFUSED - are answered
# by the row below; only the third wants any prose, and the refusal reason is what fits in a head.
# Storing the bodies would put a second copy of every tool result into the database, and this
# engagement's growth constraint (T00) is the reason not to: the state DB is 5.96 MB for 74 threads
# and one 64-call link reads about 500 KB of results. The cap is the SAME 200 `uplink.FIELD_CAP`
# already uses, rather than a number invented here.
TRANSCRIPT_HEAD_CHARS = 200
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


def context_tokens() -> int:
    """The context window the endpoint actually serves, DECLARED (`0` = not declared).

    **Declared rather than discovered, and that is not a shortcut.** The window cannot be read over
    the OpenAI surface (`/v1/models` carries no `num_ctx`), so the only honest figure is the one the
    operator states. It lives HERE, beside the other budget figure, because it is a property of the
    resolved target rather than of the check that reads it - and `0` means UNDECLARED, the same
    sentinel `tool_output_chars` uses for "unlimited", because a caller unable to tell "no window"
    from "nobody said" would report a fit it never checked.

    **Before 2026-09-22 this was a bare `os.environ` read inside `doctor`**, so the check was the
    only place the window could be seen: a run-card carrying a prompt estimate had no way to ask the
    same question, and the two would have drifted while both looked authoritative.
    """
    try:
        return int(os.environ.get("SOLAR_CONTEXT_TOKENS", "0") or 0)
    except ValueError:
        return 0


def estimate_tokens(chars: int) -> int:
    """Characters -> tokens, ONE divisor for the whole runtime (3.5 chars per token).

    **Not a new number: the divisor the tool-output budget already rests on.** 2,110,699 prompt
    tokens were measured against a figure derived from it (`cli._tool_budget_tokens`), so a second
    spelling here would let `doctor` and a run-card disagree about the same prompt while both looked
    authoritative. Both call this.
    """
    return int(chars / 3.5)


def prompt_tokens(messages: list[dict]) -> int:
    """An ESTIMATE of what the assembled prompt costs, before the first round sends it.

    **Labelled an estimate, and it is the only figure available at that moment:** the endpoint's own
    count is authoritative and arrives WITH the answer (`usage.in`), so a run that has to know what
    it is about to send cannot get it from there. Text length only - tool-call arguments, image
    parts and the provider's own formatting are outside it - so it is a FLOOR, and the card records
    it as one. See `runcard.write`, which writes it beside the window it was measured against.
    """
    return estimate_tokens(sum(len(str(m.get("content") or "")) for m in messages))


def _target_of(args: dict) -> str:
    """The ONE argument naming what a call acted on, taken in the order the tools declare it.

    **Not `json.dumps(args)`**: a `write_file`'s arguments ARE the file, so dumping them would make
    the transcript exactly the second copy this design refuses. The accountability question - did it
    touch the clone, did it write that path - is a path, and the tools name it in a closed set.
    """
    for key in ("rel", "path", "command", "pattern"):
        val = args.get(key)
        if isinstance(val, str) and val:
            return val
    return ""


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


# A local OpenAI-compatible server needs no credential, but the SDK insists on a
# non-empty string. This is the convention those projects document themselves -
# llama.cpp's examples pass `sk-no-key-required`, Ollama's pass `ollama`
# ("required but ignored"), LiteLLM's local config writes `api_key: none` - so it is a
# recognised value in a server log, not a secret someone forgot to set.
NO_KEY_PLACEHOLDER = "sk-no-key-required"

# Request-body keys the RUNNER owns. A provider's `extra_body` may add fields, but must not be
# able to replace the message list or the tool schema - silently swapping either would be a trap.
RESERVED_BODY_KEYS = ("model", "messages", "tools")


def resolved_key(runner: str = "", api_key_env: str = "",
                 keyless: bool = False) -> str | None:
    """The credential to send: a named env var, a placeholder, or nothing.

    Requiring a key the endpoint does not want is what made a local endpoint unreachable:
    `run --runner http` against a perfectly healthy Ollama/llama.cpp server fell back to the
    STUB, reported APPROVED and recorded `tokens 0/0` - a run that never happened.

    With a DECLARED provider that names a variable, only that variable is consulted: a
    provider's credential must not be silently satisfied by an unrelated key that happens to
    be set. With NO provider declared, `SOLAR_API_KEY`/`DEEPSEEK_API_KEY` behave exactly as
    before - which is the state `keyless` exists to tell apart from a declared keyless
    provider (v5.7.1):

        keyless=True                    the provider declared `api_key_env: ""`: it needs no
                                        credential, so send the placeholder and NEVER an
                                        unrelated key.
        keyless=False, api_key_env=""   nothing was declared: the legacy chain, unchanged.

    The middle case was the defect. A keyless provider collapsed into the same `""` as "no
    provider at all", so the legacy chain was consulted and `SOLAR_API_KEY` was sent as a
    bearer token to `http://localhost` - a cloud credential leaving the machine to a local
    or LAN endpoint, contradicting the promise above.
    """
    if keyless:
        return NO_KEY_PLACEHOLDER if runner == "http" else None
    if api_key_env:
        key = (os.environ.get(api_key_env) or "").strip()
        if key:
            return key
    else:
        key = api_key()
        if key:
            return key
    return NO_KEY_PLACEHOLDER if runner == "http" else None


def endpoint_label(runner: str = "", provider_name: str = "",
                   endpoint: str = "") -> str:
    """Where a run actually went, for the record.

    A DECLARED provider name is the most useful label (`local`, `openrouter`, `deepseek`),
    then the endpoint's host:port, then `stub`. Provenance, because the model id cannot carry
    it: `qwen3:8b` on a laptop and a hosted `qwen3:8b` are the same string.
    """
    if runner == "stub":
        return "stub"
    if provider_name:
        return provider_name
    parsed = urlparse(endpoint or base_url())
    return parsed.netloc or (endpoint or base_url())


def provider_family(provider_name: str = "", providers: dict | None = None) -> str:
    """Which model family the resolved endpoint speaks ("" when unknown).

    A DECLARED provider's `family` wins, because its host cannot be trusted to say: a local
    server, a LAN box and a self-hosted gateway all have hosts that match nothing in
    `MODEL_TIERS`, which is why declaring a `model_tier` against a local endpoint used to
    RAISE. Undeclared, it still infers from the host - the pre-v5.7 behaviour, unchanged.
    """
    declared = (providers or {}).get(provider_name) or {}
    if (declared.get("family") or "").strip():
        return declared["family"].strip()
    endpoint = (declared.get("base_url") or "").strip() or base_url()
    host = (urlparse(endpoint).hostname or "").lower()
    for family in MODEL_TIERS:
        if family in host:
            return family
    return ""


def resolve_tier(tier: str, family: str | None = None) -> str:
    """The concrete id for a tier. Raises when it cannot be answered honestly.

    `family=None` means "work it out from the configured endpoint"; an explicitly EMPTY family
    means "this provider has none", and must raise rather than quietly re-inferring from
    whatever endpoint happens to be in the environment - which is how a declared local provider
    resolved `fast` to a DeepSeek id.
    """
    family = provider_family() if family is None else family
    if not family:
        raise ValueError(
            f"cannot resolve model tier {tier!r}: the provider declares no `family` and no "
            f"known family matches its host - declare `family` on the provider, declare a "
            f"`models` alias for the id, or use an explicit model id")
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
    one place - a second copy would drift - so this is now a view of `resolve_target`,
    which is the same ladder plus `models` aliases and the provider the id belongs to.
    """
    target = resolve_target(cfg_model=cfg_model, role_model=role_model,
                            cfg_tier=cfg_tier, role_tier=role_tier)
    return target["model"], target["model_source"]


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


# Shipped provider table (v5.7.0). A repo names a provider and gets its endpoint and the
# NAME of the env var holding the key - never a key, because `.solar/config.json` is
# committed. Declaring `family` here is what lets a `model_tier` resolve for an endpoint
# whose host says nothing (a local server, a LAN box, a gateway).
#
# EVERY base_url below was verified on 2026-09-19 by probing it unauthenticated: 401/403 on
# `/models` - or 400 on `/chat/completions` where a provider exposes no model list - means the
# endpoint exists and wants a key; 404 means the path is wrong. Two candidates that
# "everybody knows" were dropped by that check rather than shipped on reputation.
PROVIDERS: dict[str, dict] = {
    "openai":     {"base_url": "https://api.openai.com/v1",
                   "api_key_env": "OPENAI_API_KEY"},
    "deepseek":   {"base_url": "https://api.deepseek.com",
                   "api_key_env": "DEEPSEEK_API_KEY", "family": "deepseek"},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1",
                   "api_key_env": "OPENROUTER_API_KEY"},
    "groq":       {"base_url": "https://api.groq.com/openai/v1",
                   "api_key_env": "GROQ_API_KEY"},
    "mistral":    {"base_url": "https://api.mistral.ai/v1",
                   "api_key_env": "MISTRAL_API_KEY"},
    "xai":        {"base_url": "https://api.x.ai/v1", "api_key_env": "XAI_API_KEY"},
    "together":   {"base_url": "https://api.together.xyz/v1",
                   "api_key_env": "TOGETHER_API_KEY"},
    "fireworks":  {"base_url": "https://api.fireworks.ai/inference/v1",
                   "api_key_env": "FIREWORKS_API_KEY"},
    "cerebras":   {"base_url": "https://api.cerebras.ai/v1",
                   "api_key_env": "CEREBRAS_API_KEY"},
    "anthropic":  {"base_url": "https://api.anthropic.com/v1",
                   "api_key_env": "ANTHROPIC_API_KEY"},
    "perplexity": {"base_url": "https://api.perplexity.ai",
                   "api_key_env": "PERPLEXITY_API_KEY"},
    "moonshot":   {"base_url": "https://api.moonshot.ai/v1",
                   "api_key_env": "MOONSHOT_API_KEY"},
    # Local servers: no credential, so no `api_key_env`. Nothing listens until you start one.
    "ollama":     {"base_url": "http://localhost:11434/v1", "api_key_env": ""},
    "lmstudio":   {"base_url": "http://localhost:1234/v1", "api_key_env": ""},
    "vllm":       {"base_url": "http://localhost:8000/v1", "api_key_env": ""},
    "llamacpp":   {"base_url": "http://localhost:8080/v1", "api_key_env": ""},
    # A self-hosted gateway (LiteLLM & co) in front of everything: one endpoint, one key.
    "gateway":    {"base_url": "http://localhost:4000/v1",
                   "api_key_env": "LITELLM_API_KEY"},
}


def providers_table(cfg_providers: dict | None = None) -> dict:
    """Shipped providers merged with the repo's own, per FIELD, repo wins.

    Per field so a repo can repoint one provider (`base_url` at a mirror) without
    restating its `api_key_env`, and can add a provider without touching the shipped set.
    """
    merged = {name: dict(spec) for name, spec in PROVIDERS.items()}
    for name, spec in (cfg_providers or {}).items():
        if isinstance(spec, dict):
            merged[name] = {**merged.get(name, {}), **spec}
    return merged


def resolve_target(cfg_model: str = "", role_model: str = "", cfg_tier: str = "",
                   role_tier: str = "", cfg_provider: str = "", role_provider: str = "",
                   providers: dict | None = None,
                   models: dict | None = None) -> dict:
    """Resolve ONE call's whole target: model id, provider, endpoint, credential source.

    The model ladder is unchanged (`SOLAR_MODEL` > role `model` > role `model_tier` >
    `cfg.model` > `cfg.model_tier` > default), with one addition: at EVERY rung, a value that
    names an entry in `models` is an **alias** and wins, because it is a name the repo defined
    on purpose. An alias carries its own provider, id and `extra_body`, so a model is declared
    once and referred to by name from a config, a role or a chain.

    A model id is OPAQUE. `anthropic/claude-sonnet-4.5`, a `:nitro` routing variant, a `~latest`
    alias and llama.cpp's `C:\\models\\x.gguf` are all valid ids that mean nothing here, so
    nothing in this module parses, splits or normalises one.

    Returns a dict; `base_url` empty means the env/default endpoint (the pre-v5.7 behaviour).
    Raises ValueError for an unknown provider NAME, because falling back to the default
    endpoint would silently run somewhere other than where the config pointed.
    """
    table = models if isinstance(models, dict) else {}
    known = providers or {}
    provider_hint = (role_provider or cfg_provider or "").strip()
    # A declared-but-unknown name is a config error even when an alias ends up choosing a
    # different provider: the user believes that name is in effect, and silence would mean it is
    # quietly ignored - the same defect as a typo selecting a different runner.
    if provider_hint and provider_hint not in known:
        raise ValueError(
            f"unknown provider {provider_hint!r} (have: {', '.join(sorted(known))}) - "
            f"declare it under `providers` in .solar/config.json")
    alias: dict = {}
    model, model_source = DEFAULT_MODEL, "default"

    for source, kind, value in (
            ("env SOLAR_MODEL", "id", os.environ.get("SOLAR_MODEL") or ""),
            ("role model", "id", role_model or ""),
            ("role model_tier", "tier", role_tier or ""),
            ("config model", "id", cfg_model or ""),
            ("config model_tier", "tier", cfg_tier or "")):
        value = (value or "").strip()
        if not value:
            continue
        entry = table.get(value)
        if isinstance(entry, dict) and entry.get("id"):
            alias = entry
            model = str(entry["id"])
            model_source = f"{source}={value} -> {model}"
        elif kind == "id":
            model, model_source = value, source
        else:
            model = resolve_tier(value, provider_family(provider_hint, known))
            model_source = f"{source}={value}"
        break

    # An alias owns the PAIR it declares. A model id is only meaningful at the provider that
    # serves it, so a provider named at config or ROLE level applies to ids that carry none:
    # measured before this, a role with `model: local-qwen` (alias -> local) AND
    # `provider: deepseek` sent `qwen3:8b` to api.deepseek.com - a mismatch no endpoint can
    # report, only fail. A role whose own `provider` a model alias overrules is named by
    # `doctor` (check `routing`) rather than left to be discovered.
    provider = (str(alias.get("provider") or "") or provider_hint).strip()
    if provider and provider not in known:
        raise ValueError(
            f"unknown provider {provider!r} (have: {', '.join(sorted(known))}) - declare it "
            f"under `providers` in .solar/config.json")
    spec = known.get(provider) or {}
    base = str(spec.get("base_url") or "").rstrip("/")
    # KEYLESS is three-valued, and the middle state is the one that bit: `api_key_env`
    # PRESENT and empty means the provider declared "no credential needed" (how every local
    # server is declared), while an ABSENT key means nothing was declared and the legacy env
    # chain applies. Collapsing the two sent a cloud key to localhost.
    keyless = "api_key_env" in spec and not str(spec.get("api_key_env") or "").strip()
    return {
        "model": model,
        "model_source": model_source,
        "provider": provider,
        "base_url": base,
        "endpoint": base or base_url(),
        "api_key_env": str(spec.get("api_key_env") or ""),
        "keyless": keyless,
        "headers": dict(spec.get("headers") or {}),
        "extra_body": dict(alias.get("extra_body") or {}),
    }


def target_for(cfg, role_spec: dict | None = None) -> dict:
    """The target a repo resolves to, with or without a role in hand (v5.7.1).

    ONE place for the call sites that must know a target BEFORE a node runs - the runner
    decision, `doctor`'s routing table, the bench/eval preflight - so each of them answers it
    the way the node will instead of approximating it from the environment.

    `role_spec=None` is the whole-repo answer (the config's own model and provider): the
    honest estimate when no role has been chosen yet. With a spec, this is exactly what
    `run` will do for that role.

    `cfg` is duck-typed (`.model`, `.model_tier`, `.provider`, `.providers`, `.models`) so
    the CLI, the server and the bench can all call it without a Config import.
    """
    spec = role_spec or {}
    return resolve_target(cfg_model=cfg.model, cfg_tier=cfg.model_tier,
                          role_model=spec.get("model", ""),
                          role_tier=spec.get("model_tier", ""),
                          cfg_provider=cfg.provider,
                          role_provider=spec.get("provider", ""),
                          providers=providers_table(getattr(cfg, "providers", None)),
                          models=getattr(cfg, "models", None))


# Ids a provider serves through an alias it does not list in /models. DeepSeek accepts
# `deepseek-chat` while `GET /models` returns only `deepseek-flash` and `deepseek-v4-pro`,
# so absence from that list is not proof of a bad id.
UNLISTED_ALIASES = ("deepseek-chat",)

# ------------------------------------------------------------------ the chat client's budget (v5.7.5)
#
# **STATED, because until 2026-09-20 it was INHERITED and nobody had done the arithmetic.** The
# client a chat call used was constructed with no timeout at all, so a link that hung was bounded by
# the SDK's defaults alone - a 600 s read with two retries, which is THREE of them - and the honest
# answer to "what does a hung link cost" was about thirty minutes with nothing of ours in the loop.
# Measured by T1.1 in the Promyro engagement and left unowned for four days.
#
# The two levers MULTIPLY, so the worst case is one line:
#
#     read x (1 + retries) = 180 x 3 = 540 s = 9 minutes, against 1,800 s before.
#
# `connect` is deliberately much shorter than `read`. An unreachable or black-holed host is the case
# that LOOKS like a hang while nothing is being served, and ten seconds is enough for a host that is
# going to answer at all. `read` stays generous because it bounds a model THINKING, not a transfer:
# the slowest whole run measured on this harness is 21.5 s (T2.3, in the Promyro engagement), so 180
# is an order of magnitude of headroom before a real run is failed rather than hung.
#
# **Retrying a TIMEOUT is the part worth knowing.** `APITimeoutError` subclasses
# `APIConnectionError`, so the SDK retries it by default - and each retry re-sends a request the
# provider may already have served, which costs money as well as wall time. `CHAT_MAX_RETRIES` is
# therefore part of the budget rather than a coincidence of the SDK's defaults.
CHAT_CONNECT_TIMEOUT = 10.0
CHAT_READ_TIMEOUT = 180.0
CHAT_WRITE_TIMEOUT = 30.0
CHAT_POOL_TIMEOUT = 10.0
CHAT_MAX_RETRIES = 2


def chat_client(key: str, endpoint: str, headers: dict | None = None,
                read_timeout: float = CHAT_READ_TIMEOUT,
                max_retries: int = CHAT_MAX_RETRIES):
    """The client a CHAT call uses, with its whole budget stated. See the constants above.

    A function rather than an inline construction for two reasons: the budget becomes something a
    test can assert on instead of something a reader has to check by noticing an absence, and a test
    can pass a SHORT `read_timeout` to watch a hung endpoint fail in a second rather than wait three
    minutes for the real one. `Timeout` is imported from the SDK rather than from `httpx`, which is
    the same class - `openai.Timeout is httpx.Timeout` - but does not make httpx a dependency of
    this file.
    """
    from openai import OpenAI, Timeout
    return OpenAI(api_key=key, base_url=endpoint, default_headers=headers,
                  timeout=Timeout(connect=CHAT_CONNECT_TIMEOUT, read=read_timeout,
                                  write=CHAT_WRITE_TIMEOUT, pool=CHAT_POOL_TIMEOUT),
                  max_retries=max_retries)


def known_models(timeout: float = 15.0, runner: str = "",
                 target: dict | None = None) -> tuple[list[str] | None, str]:
    """Ask the provider which model ids it serves: (ids|None, error).

    `doctor`-only. A mis-set id is otherwise invisible until the first chat call
    comes back 400 - which is how a non-existent `deepseek-v4-flash` pin sat in a
    repo config unnoticed. Never raises: doctor reports, it does not fail a run.

    Uses the same key resolution as a run, so a KEYLESS local endpoint can be listed
    (sending the placeholder is what makes it reachable at all), and the returned error is
    what lets `doctor` say "the endpoint did not answer" instead of PASS - the one check
    that answers "is my local server actually up?".
    """
    key = resolved_key(runner, (target or {}).get("api_key_env", ""),
                       bool((target or {}).get("keyless", False)))
    if key is None:
        return None, "no API key"
    endpoint = (target or {}).get("endpoint") or base_url()
    headers = (target or {}).get("headers") or None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key, base_url=endpoint, timeout=timeout,
                        default_headers=headers)
        return [m.id for m in client.models.list().data], ""
    except Exception as e:  # network, auth, or SDK failure
        return None, str(e)


def available() -> bool:
    """True when a CREDENTIAL is in the environment (the pre-v5.7.1 question)."""
    return api_key() is not None


def can_call(target: dict | None = None) -> bool:
    """True when a real model call is possible for THIS target (v5.7.1).

    `available()` answers "is a key in the environment", which is the wrong question once a
    repo can DECLARE its endpoint: a keyless local provider has no credential by design, so
    asking about a key made a fully configured local run fall back to the stub - the local
    model could not be reached from a committed config at all, only by exporting
    `SOLAR_RUNNER=http`. Measured before this fix: a config declaring
    `providers: {"local": {"base_url": "http://localhost:11434/v1", "api_key_env": ""}}`
    plus a model alias naming it, with no cloud key set, gave `select_runner("") == "stub"`.

    A DECLARED provider is answered from its own declaration, so this matches what `run`
    will do: enough to call (it needs no key, or its named variable is present) or not.
    `target=None` keeps the legacy key-only answer.
    """
    if target is None:
        return available()
    if target.get("keyless"):
        return True
    env = str(target.get("api_key_env") or "")
    if env:
        return bool((os.environ.get(env) or "").strip())
    return available()


# The three runners (v5 §3): agent-dispatch hands off to the repo's .agent.md
# agents in the IDE; http calls an OpenAI-compatible endpoint; stub is
# deterministic and offline. Kept here so the CLI can offer them as choices.
RUNNERS = ("agent-dispatch", "http", "stub")


def select_runner(cfg_runner: str = "", target: dict | None = None) -> str:
    """Resolve which runner executes specialist work (v5 §3, provider-agnostic).

    Ladder: `SOLAR_RUNNER` (env, or `run --runner`, which sets it for the run) >
    the repo's `config.json` `runner` > auto.

    Auto asks `can_call(target)` (v5.7.1): `http` when a call is possible, else `stub`. It
    used to ask only whether a key was in the environment, which cannot be the right
    question once a repo declares a KEYLESS endpoint - with no cloud key set, a repo fully
    configured for a local model resolved to the stub. `target` is passed IN rather than
    re-resolved here, for the same reason the runner itself is (TD-5.6-7): one ladder, one
    outcome, one place. Omitted, auto falls back to the key-only answer exactly as before.

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
    return "http" if can_call(target) else "stub"


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
        """One call over every layer, and the LAST line is the only error this owes.

        No ownership test to consult first: a layer answers `None` when the tool is not its own,
        so the composite tries and the name nobody claims ends here.
        """
        for layer in self.layers:
            out = layer.call_tool(name, args)
            if out is not None:
                return out
        return f"ERROR: unknown tool {name}"


class ExecutorResult(dict):
    """Thin dict: output / usage(in,out) / tool_calls / error / model / forced_final."""


def _tool_loop(client, model: str, messages: list[dict], ws, max_rounds: int,
               effort: str = "", extra_body: dict | None = None) -> ExecutorResult:
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
    usage_reported = False          # did the ENDPOINT report usage, or is 0/0 just "unknown"?
    transcript: list[dict] = []     # one row per tool call - see TRANSCRIPT_HEAD_CHARS

    def _result(output: str, err: str | None, forced: bool) -> ExecutorResult:
        # **`max_rounds` travels with the answer because `forced_final` cannot say enough on its own.**
        # A tool-less last round is produced by ANY budget that ran out - including a deliberate
        # one-round budget - so a card without the budget cannot tell "cut off" from "answered inside
        # the budget it was given", nor whether the run used 12 rounds or an env-lifted
        # `SOLAR_MAX_ROUNDS`. See `runcard.write`, which writes it.
        return ExecutorResult(output=output, usage={"in": total_in, "out": total_out},
                              tool_calls=tool_calls, error=err, model=model,
                              forced_final=forced, usage_reported=usage_reported,
                              max_rounds=rounds,
                              # A COPY, so a returned result cannot be mutated by the loop's next
                              # round - and always present, because "this link called NO tool" is
                              # itself one of the answers the transcript exists to give.
                              tool_transcript=list(transcript))

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
        if extra_body:
            # MEASURED, not assumed: the SDK REJECTS unknown keywords outright
            # (`Completions.create() got an unexpected keyword argument 'provider'`) and no
            # request leaves the process. Router fields - OpenRouter's `provider`, `models`,
            # `route`, `plugins` - have to ride in `extra_body=`, which sends them in the JSON
            # body. Reserved keys are dropped first, because an `extra_body` that silently
            # replaced the message list or the tool schema would be a trap, not a feature.
            payload["extra_body"] = {k: v for k, v in extra_body.items()
                                     if k not in RESERVED_BODY_KEYS}
        try:
            resp = client.chat.completions.create(**payload)
            if getattr(resp, "usage", None):
                usage_reported = True        # a real endpoint told us; 0/0 now means zero
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
            result = _cap_tool(ws.call_tool(tc.function.name, args))
            # **Recorded HERE, where the call is made and the round is known.** The row is what
            # lets a later reader say which tool ran, on what, in which round, and how much came
            # back - and `ok` is what turns "there is no count of refused writes" into a count
            # (`agent-tool-surface.md` section 7), because every refusal this layer produces is the
            # string `call_tool` returned, and those all begin `ERROR`.
            transcript.append({
                "n": len(transcript) + 1,
                "round": rnd,
                "tool": tc.function.name,
                "target": _target_of(args),
                "args_chars": len(tc.function.arguments or ""),
                "result_chars": len(result),
                "ok": not result.startswith("ERROR"),
                "head": result[:TRANSCRIPT_HEAD_CHARS],
            })
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
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
        usage={"in": 0, "out": 0}, tool_calls=0, error=None, model="stub",
        provider="stub", usage_reported=False)


def run(role: str, system_prompt: str, objective: str, repo: Path,
        cfg_model: str = "", max_rounds: int | None = None,
        spec: dict | None = None, human_approval: bool = False,
        cfg_reasoning: str = "", cfg_tier: str = "", runner: str = "",
        cfg_provider: str = "", providers: dict | None = None,
        models: dict | None = None, target: dict | None = None,
        clone: str = "") -> ExecutorResult:
    """Run one specialist node: system prompt + objective, with workspace tools.

    `spec` is the role's registry entry (v5 §6). It is handed to the tool layers so
    policy derives from the ROLE, not the process: which tools are offered, where the
    role may write, and which commands it may run. Its `model` is the per-node model
    override (TD-5.4-1), its `reasoning` the per-node effort (TD-5.4-2) and its
    `provider` the per-node endpoint (v5.7.0). `human_approval` reaches the command
    layer's approval gate.

    `runner` is the ALREADY-RESOLVED runner from `select_runner` (TD-5.6-7). It is
    passed in rather than re-resolved here because one ladder must have one outcome.

    `providers`/`models` are the resolved tables (see `providers_table`); the target they
    produce decides the endpoint, the credential SOURCE, any request headers and any extra
    request-body fields. An empty target means the env/default endpoint - the behaviour
    from before a provider could be declared.

    `target` (v5.7.1) is that same resolution, already done by the caller (`target_for`).
    The node's runner decision needs the target BEFORE this call, so resolving it twice
    would mean two chances to disagree; passed in, it is resolved once per node. Omitted,
    it is resolved here - and a config error still REJECTS the run rather than quietly
    reaching an endpoint nobody asked for.

    `clone` (T50, 2026-09-23) shares not one word with `target`, and the two are the
    two senses of "target" this runtime has. `target` is the ENDPOINT the node talks to;
    `clone` is WHICH CLONE the run is about, and it reaches the command layer so that a
    declaration spelled `repos/{clone}` can resolve. `""` is the run declaring `none`,
    which every clone-scoped command refuses rather than defaulting to one.

    Falls back to a stub (no network) when the endpoint cannot be reached at all, so the
    graph stays runnable/testable without credentials.
    """
    if runner == "stub":
        return stub_result(role, objective, "runner=stub, by request")
    if target is None:
        try:
            target = resolve_target(
                cfg_model=cfg_model, role_model=(spec or {}).get("model", ""),
                cfg_tier=cfg_tier, role_tier=(spec or {}).get("model_tier", ""),
                cfg_provider=cfg_provider, role_provider=(spec or {}).get("provider", ""),
                providers=providers, models=models)
        except ValueError as e:
            # An unresolvable tier and an unknown provider NAME are both configuration errors,
            # and the honest place for them is the error path: the review node REJECTS the run
            # instead of approving output produced somewhere nobody asked for.
            return ExecutorResult(output=f"ERROR: {e}", usage={"in": 0, "out": 0},
                                  tool_calls=0, error=str(e), model="unresolved",
                                  provider="unresolved", usage_reported=False)
    label = endpoint_label(runner, target["provider"], target["endpoint"])
    key = resolved_key(runner, target["api_key_env"], bool(target.get("keyless")))
    if key is None:
        why = (f"no {target['api_key_env']} set" if target["api_key_env"]
               else "no SOLAR_API_KEY set")
        return stub_result(role, objective, why)
    try:
        client = chat_client(key, target["endpoint"], target["headers"] or None)
    except Exception as e:  # pragma: no cover - import/init failure
        return ExecutorResult(output=f"ERROR initializing client: {e}",
                              usage={"in": 0, "out": 0}, tool_calls=0, error=str(e),
                              model=target["model"], provider=label,
                              usage_reported=False)
    ws = _ToolLayer(Workspace(repo, spec),
                    CommandRunner(repo, spec, human_approval=human_approval,
                                  role=role, clone=clone))
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
    # **Taken BEFORE the loop, because the loop MUTATES `messages`** - tool results, the budget
    # notice, the final instruction all land in that list - so a figure read afterwards would
    # describe the last round of a run that had already happened.
    base_prompt = prompt_tokens(messages)
    # `None` is "nobody narrowed it", which is NOT the same as the default: the spec is what carries
    # a role's own declaration, and this is the only call site that has it. See `round_budget`.
    rounds = round_budget(spec) if max_rounds is None else max_rounds
    res = _tool_loop(client, target["model"], messages, ws, rounds, effort,
                     extra_body=target["extra_body"])
    # Provenance travels with the result: the graph records it, and the run-card is how a
    # local run is told apart from a cloud run of the same model id.
    res["provider"] = label
    # **What the run was about to send, and the window it had been told it was sending it into.**
    # Both travel, because the estimate alone is half a fact: the window is declared per install and
    # can be raised between two runs, so a card holding one of them cannot be judged.
    res["prompt_tokens"] = base_prompt
    res["context_tokens"] = context_tokens()
    return res
