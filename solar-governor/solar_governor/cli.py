"""solar-governor CLI: init | run | doctor (v5 §9 install surface)."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from . import bench, chain, eval as eval_mod, executor, install, runcard, server, uplink
from .core import Config
from .core import read_json
from .graph import build_graph, pending_interrupt, run_step, run_task
from .ledger import record
from .registry import chains as load_chains
from .registry import declared as declared_roles
from .registry import load as load_registry
from .registry import role_keys

# exit codes for the --json step contract (agent wrapper drives on these)
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_AGENT_DISPATCH = 10   # paused: run the specialist, resume with --result
EXIT_REVIEW = 11           # paused: ask the human, resume with --approve
EXIT_REJECTED = 12         # the graph completed, but the verdict is REJECTED


def _cfg_path(root: Path) -> Path:
    return root / ".solar" / "config.json"


def cmd_init(args):
    """Create or REFRESH an install, without destroying what the repo chose.

    Re-running this used to overwrite `config.json` (losing a model pin) while writing
    `registry.json` only if absent - so nobody re-ran it, and installs drifted from the
    runtime. Now: existing settings win, new keys are added, the version marker is
    written, and the generated `.gitignore` block is rewritten in place. Explicit CLI
    flags still beat the stored value, because that is what a flag means.
    """
    root = Path(args.repo).expanduser().resolve()
    solar = root / ".solar"
    (solar / "state").mkdir(parents=True, exist_ok=True)

    existing = install.read_config(root)
    fresh = Config().to_dict()
    merged = install.merge_config(existing, fresh)
    # explicit flags beat what is stored; an absent flag never resets a repo's choice
    if getattr(args, "profile", None):
        merged["profile"] = args.profile
    if getattr(args, "approval", False):
        merged["human_approval"] = True
    if getattr(args, "runner", ""):
        merged["runner"] = args.runner

    # `repo` is dropped when it only restates where this file already lives - that is
    # what makes the config portable. A path pointing elsewhere is a deliberate (and
    # unusual) setup, so it is kept, and said out loud.
    explicit_repo = ""
    if (merged.get("repo") or "").strip():
        if Path(merged["repo"]).expanduser().resolve() == root:
            merged.pop("repo", None)
        else:
            explicit_repo = merged["repo"]

    added = sorted(set(merged) - set(existing)) if existing else []
    tuned = sorted(k for k, v in (existing or {}).items()
                   if k in merged and merged[k] != fresh.get(k))
    _cfg_path(root).write_text(json.dumps(merged, indent=2), encoding="utf-8")
    cfg = Config.load(_cfg_path(root))          # reload so `root` derives the same way

    reg_path = solar / "registry.json"
    if not reg_path.exists():
        reg_path.write_text(json.dumps(load_registry(None), indent=2), encoding="utf-8")

    ignore = install.sync_gitignore(root)
    install.write_version(root)

    state = "refreshed" if existing else "created"
    print(f"✅ init — {state}: profile={cfg.profile} runner={cfg.runner or 'auto'} in {root}")
    print(f"   config : {_cfg_path(root).relative_to(root)}"
          + (f" (kept: {', '.join(tuned)})" if tuned else "")
          + (f" (added: {', '.join(added)})" if added else ""))
    print(f"   version: {install.VERSION_FILE} -> {install.read_version(root)}")
    print(f"   ignore : .gitignore {ignore['action']}")
    if explicit_repo:
        print(f"   ⚠️  repo: an explicit path outside this directory is kept ({explicit_repo})")
    for line_no, rule in ignore["stale"]:
        print(f"   ⚠️  .gitignore:{line_no} '{rule}' sits OUTSIDE the generated block and "
              f"still applies — delete it if that path should be tracked")
    print(f"   next: solar-governor run \"<task>\"  |  solar-governor doctor")


def cmd_run(args):
    root = Path(args.repo).expanduser().resolve()
    try:
        cfg = Config.load(_cfg_path(root))
    except (OSError, ValueError) as e:
        # A config that cannot be read or parsed is a USAGE/STATE error, so it gets the
        # documented code and a message. It used to escape as a raw traceback and exit 1,
        # which is outside the contract every wrapper in this repo drives on.
        print(f"❌ {e}", file=sys.stderr)
        print(f"   config: {_cfg_path(root)}", file=sys.stderr)
        sys.exit(EXIT_USAGE)
    thread = args.thread or "t1"
    started = time.time()
    if getattr(args, "runner", ""):
        # `--runner` is a typed front door for SOLAR_RUNNER, the per-run override
        # (TD-5.4-9). Deliberately NOT written to config.json: the whole point is
        # to exercise a runner without mutating a live engagement's config. The
        # env var is what `select_runner` reads, so the flag and the knob cannot
        # disagree about which runner won.
        os.environ["SOLAR_RUNNER"] = args.runner
    try:
        # The target is resolved here for the BANNER: no role has been classified yet, so
        # this is the whole-repo answer. Each node resolves its OWN target (v5.7.1).
        runner = executor.select_runner(cfg.runner, executor.target_for(cfg))
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(2)
    if args.chain and args.role:
        print("❌ --chain and --role are mutually exclusive", file=sys.stderr)
        sys.exit(2)
    if args.role:
        reg = load_registry(cfg.root / ".solar" / "registry.json")
        if args.role not in role_keys(reg):
            print(f"❌ no role '{args.role}' in registry (have: {role_keys(reg)})",
                  file=sys.stderr)
            sys.exit(2)
    if args.chain:
        cm = load_chains(cfg.root / ".solar" / "registry.json")
        if args.chain not in cm:
            print(f"❌ no chain '{args.chain}' in registry (have: {sorted(cm)})",
                  file=sys.stderr)
            sys.exit(2)
        if not getattr(args, "auto", False):
            print("❌ chains are driver-orchestrated: run the whole chain headless with "
                  "`--chain <name> --auto`, or in the IDE drive each link as its own "
                  "`--role` dispatch from the Governor agent (a bare `--chain` no "
                  "longer dispatches a self-running chain entry).", file=sys.stderr)
            sys.exit(2)
        return _cmd_run_chain_auto(cfg, args, thread)
    if args.json:
        return _cmd_run_json(cfg, args, thread, started)
    # interactive/one-shot path (stdin prompts at interrupts)
    state = run_task(cfg, args.task, thread=thread, approve=args.approve,
                     resume_result=args.result, chain=args.chain or "",
                     role=args.role or "")
    _write_artifacts(cfg, state, thread, started)
    chain = f" chain={state.get('chain')}" if state.get("chain") else ""
    print(f"✅ run complete — stage={state.get('stage')} verdict={state.get('verdict')} "
          f"role={state.get('role')}{chain} runner={runner}")
    print(f"   model={state.get('model')} tokens: in={state.get('tokens_in',0)} "
          f"out={state.get('tokens_out',0)} tool_calls={state.get('tool_calls',0)}")
    out = state.get("output", "")
    print(f"   output:\n{out}")
    print(f"   ledger: {cfg.ledger_path}")
    print(f"   run-card: {cfg.root / '.solar' / 'runs' / f'{thread}.json'}")
    sys.exit(_exit_for(state))


def _cmd_run_chain_auto(cfg, args, thread) -> None:
    """Headless auto-chain: run the whole named chain link-by-link (http/stub)."""
    agg = chain.run_chain(cfg, args.chain, args.task, thread=thread)
    chain.print_chain(agg)


def _write_artifacts(cfg, state, thread, started) -> None:
    """Write this run's ledger section + run-card from a state snapshot.

    Called at every --json step so progress is on disk even when the run is paused at
    an interrupt. `ledger.record` updates THIS run's own section, so stepping three
    times leaves one section rather than three; the run-card is overwritten per step.
    The uplink push happens last, on the finished record.
    """
    record(cfg, state, thread)
    runcard.write(cfg, state, thread, started)
    line = uplink.push(cfg, state, thread)
    if line:
        print(f"   {line}")


def _exit_for(state: dict) -> int:
    """Exit code for a completed step (TD-5.4-10).

    A REJECTED verdict is NOT success. The text "0 complete" invited a wrapper to
    read a hard failure as a pass: every `max_rounds` failure in the v5.4.1
    integration test exited 0 while carrying `verdict: REJECTED`. "The graph
    reached its end" and "the work was accepted" are different claims, so they get
    different codes.
    """
    return EXIT_REJECTED if state.get("verdict") == "REJECTED" else EXIT_OK


def _state_summary(state: dict) -> dict:
    return {k: state.get(k) for k in
            ("objective", "role", "materials_status", "stage", "verdict",
             "attempts", "tokens_in", "tokens_out", "tool_calls", "error",
             "forced_final", "provider", "usage_reported")}


def _json_out(obj: dict, code: int) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))
    sys.exit(code)


def _cmd_run_json(cfg, args, thread, started) -> None:
    """One graph step, machine-readable (agent wrapper / non-interactive).

    Exit codes: 0 complete · 10 paused at agent-dispatch · 11 paused at review ·
    2 usage/state error. The task string must be identical across a thread's
    resume calls (it only seeds a fresh thread; resume uses the checkpoint).
    """
    resume = None
    if args.result is not None:
        resume = args.result
    elif args.approve is not None:
        if args.approve not in ("approve", "deny"):
            _json_out({"status": "error",
                       "message": "--approve must be 'approve' or 'deny'"}, EXIT_USAGE)
            return
        resume = "approve" if args.approve == "approve" else "deny"

    pending = pending_interrupt(cfg, thread)
    if pending is not None and resume is None:
        _json_out({"status": "error",
                   "message": (f"thread '{thread}' is paused at an interrupt "
                                f"({pending.get('kind')}) — resume with "
                                f"--result <file> or --approve approve|deny")},
                  EXIT_USAGE)
        return
    if pending is None and resume is not None:
        _json_out({"status": "error",
                   "message": (f"thread '{thread}' has no pending interrupt to "
                                f"resume — start with `run \"<task>\" --json`")},
                  EXIT_USAGE)
        return

    state = run_step(cfg, args.task, thread, resume=resume, chain=args.chain or "",
                     role=args.role or "")
    _write_artifacts(cfg, state, thread, started)

    if "__interrupt__" in state:
        payload = state["__interrupt__"][0].value
        kind = payload.get("kind", "review")
        if kind == "agent-dispatch":
            _json_out({"status": "interrupt", "kind": "agent-dispatch",
                       "thread": thread,
                       "role": payload.get("role") or state.get("role", ""),
                       "attempt": payload.get("attempt", state.get("attempts", 0)),
                       "handoff": payload.get("handoff", ""),
                       "ask": payload.get("ask", ""),
                       "state": _state_summary(state)}, EXIT_AGENT_DISPATCH)
            return
        _json_out({"status": "interrupt", "kind": "review", "thread": thread,
                   "ask": payload.get("ask", "approve or deny?"),
                   "role": state.get("role", ""),
                   "state": _state_summary(state)}, EXIT_REVIEW)
        return

    _json_out({"status": "complete", "thread": thread,
               "stage": state.get("stage"), "verdict": state.get("verdict"),
               "role": state.get("role"), "attempts": state.get("attempts", 0),
               "model": state.get("model", "stub"),
               "provider": state.get("provider", ""),
               "output": state.get("output", ""),
               "ledger": str(cfg.ledger_path),
               "run_card": str(cfg.root / ".solar" / "runs" / f"{thread}.json"),
               "state": _state_summary(state)}, _exit_for(state))


def cmd_doctor(args):
    root = Path(args.repo).expanduser().resolve()
    cfg_path = _cfg_path(root)
    checks: dict[str, tuple] = {}
    try:
        cfg = Config.load(cfg_path)
        checks["config"] = ("PASS", "")
    except Exception as e:
        checks["config"] = ("FAIL", str(e))
        _print_doctor(checks)
        sys.exit(1)
    # CREATABILITY, not existence (v5.6.3). The checkpoint directory is created on demand by
    # `run_step`/`pending_interrupt`, and `state/` is gitignored while `config.json` is
    # tracked - so a fresh clone legitimately has no `state/`. Testing existence reported
    # FAIL for a repo that runs perfectly well.
    try:
        cfg.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checks["checkpoint-writable"] = ("PASS", f"{cfg.state_dir} (created on demand)")
    except OSError as e:
        checks["checkpoint-writable"] = ("FAIL", f"cannot create {cfg.state_dir}: {e}")
    try:
        build_graph(cfg)
        checks["graph-compiles"] = ("PASS", "")
    except Exception as e:
        checks["graph-compiles"] = ("FAIL", str(e))
    reg: dict = {}
    try:
        reg_path = root / ".solar" / "registry.json"
        reg = load_registry(reg_path)
        n_roles = len(role_keys(reg))
        n_declared = len(declared_roles(reg_path))
        cm = load_chains(reg_path)
        # The merged count is what can be DISPATCHED, which is not the same as what the
        # repo wrote: `load` merges the built-in specialists under the repo's. Both
        # numbers, because "10 specialists" for a repo that declares 7 reads as a bug.
        detail = f"{n_roles} dispatchable"
        if n_declared and n_declared != n_roles:
            detail += f" ({n_declared} declared + {n_roles - n_declared} built-in)"
        if cm:
            detail += f", chains: {sorted(cm)}"
        checks["registry"] = ("PASS", detail)
    except Exception as e:
        checks["registry"] = ("FAIL", str(e))
    runner = ""
    try:
        # Asked about the repo's OWN target, not about the environment (v5.7.1): a declared
        # keyless endpoint is callable with no key at all, which is the whole point of
        # declaring a local provider.
        target = executor.target_for(cfg)
        runner = executor.select_runner(cfg.runner, target)
        detail = {"agent-dispatch": "hand off to .agent.md agents in the IDE",
                  "http": "OpenAI-compatible chat calls with workspace tools",
                  "stub": "deterministic and offline: no provider call at all"}[runner]
        if not executor.can_call(target):
            # Whatever is missing, NAME it. v5.6.4: no key is no longer a defect for `http` -
            # a placeholder is sent, which a keyless endpoint ignores and a cloud one rejects
            # with a 401. What IS worth saying is which of the two situations this is.
            missing = target["api_key_env"] or "SOLAR_API_KEY"
            note = (f"no {missing}: a request would still be sent (a placeholder), which a "
                    f"keyless local endpoint ignores and a cloud one answers with 401"
                    if runner == "http" else
                    f"no {missing} and no runner chosen: auto selects the stub, so no "
                    f"provider call will be made")
            checks["runner"] = ("PASS", f"{runner} ({detail}) — {note}")
        else:
            checks["runner"] = ("PASS", f"{runner} ({detail})")
    except ValueError as e:
        checks["runner"] = ("FAIL", str(e))
    checks["provider"] = _provider_check(cfg)
    checks["model"] = _model_check(cfg, reg, runner)
    checks["routing"] = _routing_check(cfg, reg)
    checks["uplink"] = uplink.status(cfg)
    checks["install"] = install.version_status(root)
    if args.json:
        print(json.dumps({k: {"status": v[0], "detail": v[1]} for k, v in checks.items()}, indent=2))
        return
    _print_doctor(checks)
    sys.exit(1 if any(v[0] == "FAIL" for v in checks.values()) else 0)


def _provider_check(cfg) -> tuple:
    """What this repo declares, and which entry will be used (v5.7.0).

    A declaration-only overview: it never prints a credential, only whether the named env
    var is present, because the whole point of `api_key_env` is that the config names a
    variable instead of holding a secret.
    """
    declared = cfg.providers if isinstance(cfg.providers, dict) else {}
    aliases = cfg.models if isinstance(cfg.models, dict) else {}
    shipped = len(executor.PROVIDERS)
    custom = sorted(n for n in declared if n not in executor.PROVIDERS)
    overrides = sorted(n for n in declared if n in executor.PROVIDERS)
    detail = f"{shipped} shipped"
    if custom:
        detail += f" + {len(custom)} declared: {', '.join(custom[:4])}"
    if overrides:
        detail += f"; overrides: {', '.join(overrides[:4])}"
    if aliases:
        names = ", ".join(sorted(aliases)[:4])
        detail += f"; {len(aliases)} model alias(es): {names}"
    detail += f"; selected: {cfg.provider or 'env/default endpoint'}"
    if cfg.provider and cfg.provider not in executor.providers_table(declared):
        return "FAIL", f"unknown provider {cfg.provider!r} - {detail}"
    return "PASS", detail


def _routing_check(cfg, reg: dict) -> tuple:
    """Which role reaches where, before anything runs (v5.7.1).

    `model` answers "what id does this REPO resolve to", which is a different question from
    "where does each ROLE go": a registry can put its reasoner in the cloud and its fast
    steps on a local model, and the thing worth seeing is the per-role endpoint plus whether
    that endpoint's credential is present. Only roles that name a model, a tier or a provider
    are listed - one that declares none is on the config's target, already reported above.

    A role whose own `provider` an alias overrules is named, not left to be discovered: the
    model decides the endpoint, so that `provider` is not in effect.
    """
    if not reg:
        # Saying "no role routes itself" under a FAILED registry read would be a report about
        # a file that was never read.
        return "PASS", "no registry entries to route (see the `registry` check above)"
    rows: list[str] = []
    conflicts: list[str] = []
    for role, spec in sorted(reg.items()):
        if not isinstance(spec, dict) or "system" not in spec:
            continue                      # playbook/chain entries are not dispatchable roles
        if not (spec.get("model") or spec.get("model_tier") or spec.get("provider")):
            continue
        try:
            t = executor.target_for(cfg, spec)
        except ValueError as e:
            return "FAIL", f"{role}: {e}"
        env = t["api_key_env"]
        if t.get("keyless"):
            state = "no key needed"
        elif env:
            state = f"{env} {'set' if os.environ.get(env) else 'NOT set'}"
        else:
            state = f"SOLAR_API_KEY {'set' if executor.api_key() else 'NOT set'}"
        where = t["provider"] or executor.endpoint_label("http", "", t["endpoint"])
        rows.append(f"{role} -> {t['model']} @ {where} [{state}]")
        alias = (cfg.models or {}).get(str(spec.get("model") or ""))
        alias_provider = alias.get("provider") if isinstance(alias, dict) else None
        if spec.get("provider") and alias_provider and alias_provider != spec["provider"]:
            conflicts.append(
                f"{role}: its own provider {spec['provider']!r} is NOT in effect - the model "
                f"alias {spec.get('model')!r} names {alias_provider!r}, and the model decides "
                f"the endpoint")
    if not rows:
        return "PASS", ("no role names a model or a provider - every role uses the "
                        "config's target")
    detail = f"{len(rows)} role(s) route themselves\n" + "\n".join(rows)
    if conflicts:
        return "WARN", detail + "\n" + "\n".join(conflicts)
    return "PASS", detail


def _model_check(cfg, reg: dict, runner: str = "") -> tuple:
    """Report the model that will ACTUALLY run, and where it came from (TD-5.4-6).

    Otherwise the only way to discover that `SOLAR_MODEL` is set in the shell, or that
    the config pins an id the provider does not serve, is to watch the first run fail.
    Role overrides are named too, since a role's `model` now beats the config and can
    therefore hide a stale pin.

    `runner` is passed in so the model LIST probe resolves its key the same way a run
    does. That is what lets a keyless local endpoint be listed at all, and what turns
    "the endpoint did not answer" into a WARN instead of a PASS - the check that answers
    "is my local server actually up?"
    """
    providers = executor.providers_table(cfg.providers)
    try:
        target = executor.resolve_target(cfg_model=cfg.model, cfg_tier=cfg.model_tier,
                                         cfg_provider=cfg.provider, providers=providers,
                                         models=cfg.models)
    except ValueError as e:
        return "FAIL", str(e)
    model, source = target["model"], target["model_source"]
    # Two model PLANES exist and they are named differently: the IDE pins display names
    # (`model: DeepSeek V4 Flash (deepseek)` in .agent.md frontmatter) while the runtime
    # needs the provider's API id. Transcribing between them is how a phantom
    # `deepseek-v4-flash` reached a config, so catch that shape before even probing.
    if any(ch in model for ch in " ()"):
        return "WARN", (f"{model!r} (from {source}) looks like an IDE display name; the "
                        f"runtime needs the provider's API id (e.g. deepseek-flash)")
    overrides = sorted(r for r, spec in (reg or {}).items()
                       if isinstance(spec, dict)
                       and (spec.get("model") or spec.get("model_tier")))
    effort = executor.reasoning_effort(cfg.reasoning_effort)
    detail = f"{model} (from {source}"
    if target["provider"]:
        # WHICH endpoint, and whether its credential is even present - the name only, never a
        # value. A provider whose api_key_env is unset is the likeliest reason a run fails on
        # a correctly named model, and it is otherwise invisible until the first call.
        key_env = target["api_key_env"]
        state = (f"{key_env} set" if os.environ.get(key_env) else f"{key_env} NOT set") \
            if key_env else "no key needed"
        detail += (f"; provider {target['provider']} @ {target['endpoint']} [{state}]")
    if overrides:
        shown = ", ".join(overrides[:4]) + ("..." if len(overrides) > 4 else "")
        detail += f"; {len(overrides)} role(s) override: {shown}"
    if effort:
        detail += f"; reasoning_effort={effort}"
    detail += ")"
    ids, err = executor.known_models(runner=runner, target=target)
    if ids is None:
        if err == "no API key":
            # nothing to compare against, and nothing was asked: not a WARN
            return "PASS", detail
        # A 404 is NOT "the server is down": some providers (Google's OpenAI-compat surface,
        # Perplexity) simply expose no model list. Reporting that as unreachable would be a
        # wrong signal about a working endpoint.
        lowered = err.lower()
        if "404" in lowered or "not found" in lowered:
            return "WARN", (f"{detail} - the endpoint exposes no model list, so the id could "
                            f"not be verified")
        # The endpoint did not answer. A silent PASS here would be a report about a run
        # that cannot happen - and for a local endpoint it is the one signal that the
        # server is down rather than merely slow.
        return "WARN", f"{detail} — cannot list its models ({err[:100]})"
    if model in ids or model in executor.UNLISTED_ALIASES:
        return "PASS", f"{detail} [provider serves {len(ids)} id(s)]"
    return "WARN", (f"{detail} - not in the provider's model list "
                    f"({', '.join(ids)}); may be an alias, or a typo")


def _print_doctor(checks: dict[str, tuple]) -> None:
    """Print checks one per line, indenting a detail that continues on later lines.

    A check whose detail is a TABLE (routing: one line per role) reads as a table only if the
    continuation lines are indented under the check they belong to. No existing detail
    contains a newline, so their output is unchanged.
    """
    marks = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
    for name, (status, detail) in checks.items():
        mark = marks.get(status, "?")
        lines = str(detail or "").split("\n")
        print(f"{mark} {name}: {status}{(' - ' + lines[0]) if lines[0] else ''}")
        for extra in lines[1:]:
            print(f"    {extra}")


def main():
    ap = argparse.ArgumentParser(prog="solar-governor", description="SOLAR-Ralph v5 runtime")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="initialise or refresh .solar config + registry")
    p_init.add_argument("--repo", default=".")
    p_init.add_argument("--profile", choices=["light", "full"], default=None,
                        help="override the profile; omitted on a refresh, the stored "
                             "value is kept")
    p_init.add_argument("--approval", action="store_true",
                        help="turn human_approval ON (there is no --no-approval: edit the "
                             "config to turn it off)")
    p_init.add_argument("--runner", choices=["agent-dispatch", "http", "stub", ""], default="",
                        help="how specialists execute (omitted: keep the stored value, or "
                             "auto = http if a key is set else stub)")
    p_init.set_defaults(fn=cmd_init)

    p_run = sub.add_parser("run", help="run a task through the graph")
    p_run.add_argument("task")
    p_run.add_argument("--repo", default=".")
    p_run.add_argument("--thread", default=None)
    p_run.add_argument("--chain", default=None,
                       help="run a named chain from the registry (driver-orchestrated): "
                            "with --auto it runs every link headless in order (one "
                            "run-card per link). Bare --chain (no --auto) is rejected — "
                            "in the IDE drive each link with --role from the Governor "
                            "agent.")
    p_run.add_argument("--auto", action="store_true",
                       help="with --chain: run the whole chain headless via the driver "
                            "(http/stub, one run-card per link). Required — chains are "
                            "driver-orchestrated (no self-running entry).")
    p_run.add_argument("--role", default=None,
                       help="pin dispatch to one registry role (skip keyword classify) — "
                            "e.g. a Hermes intake decision")
    p_run.add_argument("--approve", choices=["approve", "deny"], default=None)
    p_run.add_argument("--runner", choices=list(executor.RUNNERS), default=None,
                       help="run THIS task with another runner without touching "
                            "config.json (sets SOLAR_RUNNER for this run) — e.g. "
                            "exercise the http path on a repo that pins "
                            "agent-dispatch")
    p_run.add_argument("--result", default=None,
                       help="agent-dispatch: supply the agent result text/path non-interactively")
    p_run.add_argument("--json", action="store_true",
                       help="one graph step, machine-readable (exit 0 complete · "
                            "10 agent-dispatch · 11 review · 12 rejected · 2 error)")
    p_run.set_defaults(fn=cmd_run)

    p_doct = sub.add_parser("doctor", help="install self-check")
    p_doct.add_argument("--repo", default=".")
    p_doct.add_argument("--json", action="store_true")
    p_doct.set_defaults(fn=cmd_doctor)

    p_serve = sub.add_parser("serve", help="run the headless HTTP API (POST /run)")
    p_serve.add_argument("--repo", default=".")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8787)
    p_serve.set_defaults(fn=lambda a: server.serve(a.repo, a.host, a.port))

    p_bench = sub.add_parser("bench", help="run a task N times and aggregate numbers")
    p_bench.add_argument("--repo", default=".")
    p_bench.add_argument("--task", required=True)
    p_bench.add_argument("--n", type=int, default=3)
    p_bench.add_argument("--role", default="")
    p_bench.add_argument("--chain", default="")
    p_bench.set_defaults(fn=lambda a: bench.run(a.repo, a.task, a.n, a.role, a.chain))

    p_eval = sub.add_parser("eval", help="run the known-answer battery (quality signal)")
    p_eval.add_argument("--repo", default=".")
    p_eval.add_argument("--cases", default=None, help="path to a JSON cases file")
    p_eval.add_argument("--n", type=int, default=1)
    p_eval.add_argument("--id", default=None, help="run a single case by id")
    p_eval.set_defaults(fn=lambda a: eval_mod.run(a.repo,
                                                  cases=(read_json(a.cases)
                                                         if a.cases else None),
                                                  n=a.n, only=a.id))

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
