"""solar-governor CLI: init | run | doctor (v5 §9 install surface)."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from . import bench, chain, eval as eval_mod, executor, install, runcard, server, uplink
from .commands import clone_problem, clone_required, declares_clone, load_vocabulary
from .core import Config
from .core import read_json
from .graph import build_graph, pending_interrupt, run_step, run_task
from .ledger import record
from .registry import chains as load_chains
from .registry import declared as declared_roles
from .registry import load as load_registry
from .registry import role_keys
from .workspace import MAX_READ_CHARS, Workspace

# exit codes for the --json step contract (agent wrapper drives on these)
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_AGENT_DISPATCH = 10   # paused: run the specialist, resume with --result
EXIT_REVIEW = 11           # paused: ask the human, resume with --approve
EXIT_REJECTED = 12         # the graph completed, but the verdict is REJECTED


def _cfg_path(root: Path) -> Path:
    return root / ".solar" / "config.json"


def _pinned_roles(args, cfg) -> list[str]:
    """The roles this invocation PINS: a chain's entries, or one `--role`.

    **Empty does not mean "none in it" - it means "not knowable yet".** With neither flag the
    classifier picks the role, so which commands will be reachable is a fact the run learns after
    it starts. `_clone_refusal` says so rather than guessing, and the refusal then lands at the
    first call that needs a target (`CommandRunner._cwd`).
    """
    if getattr(args, "role", None):
        return [str(args.role)]
    if not getattr(args, "chain", None):
        return []
    raw = load_chains(cfg.root / ".solar" / "registry.json").get(args.chain) or []
    return [r for item in raw for r in (item if isinstance(item, list) else [item])]


def _clone_refusal(args, cfg, vocabulary: dict) -> str:
    """Why this run cannot start for want of a target clone, or `""` when it can.

    **Three refusals, in the order a caller can act on them, and all of them BEFORE a dispatch.**
    The requirement itself is read from the DECLARATION (`clone_required`), so an install whose
    commands are all engagement-rooted never sees any of this.

    1. **No `--clone` at all.** A clone-scoped command has nothing to resolve against, and the
       whole item exists because the old answer - a name baked into the declaration - credited a
       pass to the wrong repository silently.
    2. **`--clone none` when the run PINS a role that cannot work without one.** Declaring `none`
       is honest for the record-keeping roles; declaring it for a chain that opens with
       `implementer` is a declaration that provably cannot hold, and it is knowable here instead of
       at the first call - where the cost is a dispatched link that fails.
    3. **A clone that does not resolve.** Validated with `clone_problem`, which is the same two
       steps `_cwd` takes (escape refused, directory must exist) run once, at the start.
    """
    if not clone_required(vocabulary):
        return ""
    if not getattr(args, "clone", None):
        return ("this install's commands run inside a CLONE, so a run has to say which one: "
                "`--clone <name>` for a run that acts on one, or `--clone none` for a run that "
                "does not. Refusing rather than defaulting, because a default here is a run "
                "credited to a repository nobody named.")
    if args.clone == "none":
        roles = _pinned_roles(args, cfg)
        if not roles:
            return ""
        registry = load_registry(cfg.root / ".solar" / "registry.json")
        blockers = sorted({f"`{role}` holds `{name}`"
                           for role in roles
                           for name in (registry.get(role) or {}).get("exec_allow") or []
                           if isinstance(vocabulary.get(str(name)), dict)
                           and declares_clone(vocabulary[str(name)])})
        if blockers:
            return (f"--clone none cannot hold for this run: {', '.join(blockers)}, and this run "
                    f"pins the role that holds them. Name the clone the work is about.")
        return ""
    problem = clone_problem(cfg.root, str(args.clone), vocabulary)
    if problem:
        return f"--clone {args.clone!r} is not a target: {problem}"
    return ""


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
    # **WHICH CLONE THIS RUN IS ABOUT, SETTLED BEFORE ANYTHING IS DISPATCHED** (T50, 2026-09-23),
    # and before the `--chain` block below can dispatch a whole chain headless.
    refusal = _clone_refusal(args, cfg, load_vocabulary(cfg.root))
    if refusal:
        print(f"❌ {refusal}", file=sys.stderr)
        sys.exit(EXIT_USAGE)
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
                     role=args.role or "", clone=getattr(args, "clone", None) or "")
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
    """The machine interface, and it must survive an encoding it cannot see.

    `ensure_ascii=True` is deliberate, and the opposite of what this line did until
    2026-09-20. **Read, reproduced:** a redirected stdout gets the LOCALE encoding - cp1252
    on this machine - and this module prints status marks (U+2705, U+274C, U+26A0) whose code
    points are not in it, so `init | Out-File` died with `UnicodeEncodeError` and exit 1.
    Escaping non-ASCII keeps the JSON valid, keeps `json.loads` decoding to the same
    characters, and makes the payload independent of whatever console the caller has.
    **A machine interface must never depend on the terminal it is printed to.**
    """
    print(json.dumps(obj, indent=2, ensure_ascii=True))
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
                     role=args.role or "", clone=getattr(args, "clone", None) or "")
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
    checks["tool-output"] = _tool_output_check(reg, cfg.context_tokens)
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


def _tool_budget_tokens(cap_chars: int, rounds: int) -> tuple[int, int]:
    """(the largest round, the run's total input) in tokens, for `rounds` against a per-result cap.

    **Two figures, because the one that stood here was neither of them.** Every round re-sends the
    whole context, so with one capped tool result per round:

        round r carries  ~ (r - 1) x cap    -> the LARGEST round is what has to fit the served window
        summed over r    ~ cap x r(r+1)/2   -> the run's total prompt tokens, which is what you pay

    What used to print was `cap x rounds` - the total NEW text - and it was labelled a worst case.
    Measured 2026-09-22 against a real engagement link: **2,110,699 prompt tokens in**, where doctor
    had reported 27.4k.

    **The divisor lives in `executor.estimate_tokens`, called here rather than restated.** The same
    3.5 is what a run-card's own prompt estimate is built from, and two spellings would let doctor
    and a card disagree about one prompt while both looked authoritative.
    """
    per_round = executor.estimate_tokens(cap_chars)
    return per_round * max(0, rounds - 1), int(per_round * rounds * (rounds + 1) / 2)


def _rounds_for_fit(registry: dict | None) -> tuple[int, str]:
    """The LARGEST round budget any role in this registry may run under, and which role sets it.

    **`MAX_TOOL_ROUNDS` alone stopped being the answer on 2026-09-25**, when a role gained the right
    to declare its own `max_rounds`: this engagement's `recorder` asks for 24, so the install's largest
    round is TWICE what the default says - and the largest round is the single figure this check
    exists to report. Asking the resolver rather than the constant is what keeps it honest.

    A non-dict entry (`chains`, `_chains_note`) carries no `max_rounds` and resolves to the default,
    so it cannot raise the figure; no `role_keys` filter is needed for that.
    """
    best, who = executor.MAX_TOOL_ROUNDS, "the default"
    for role, spec in (registry or {}).items():
        if not isinstance(spec, dict):
            continue
        budget = executor.round_budget(spec)
        if budget > best:
            best, who = budget, f"`{role}`"
    return best, who


def _tool_output_check(registry: dict | None = None, declared: int = 0) -> tuple:
    """Is the tool-output cap sized against the context the server actually serves?

    The cap itself fails LOUDLY: `_cap_tool` keeps the head of one tool result and appends
    `...[truncated N chars to M by SOLAR_TOOL_OUTPUT_CHARS]`, so the cut is visible and the
    model can re-read a narrower range instead. The failure with NO marker is the other one -
    a cap that is fine while the WINDOW is not, so the server drops the oldest tokens (the
    system prompt and the objective) silently. Its symptom is a model that read the file and
    missed the fact, which reads as a model defect and is not one.

    **The figure that decides FIT is the largest round; the total is the cost line, not the fit
    line** - it is quadratic in rounds, because every round re-sends everything the earlier ones
    accumulated. Both are printed, and neither is called a worst case: the system prompt and the
    objective sit on top of both and doctor cannot see them. See `_tool_budget_tokens`.

    The served window cannot be read over the OpenAI surface (`/v1/models` carries no
    `num_ctx`), so it is DECLARED with `SOLAR_CONTEXT_TOKENS` rather than guessed - and when
    it is not declared the arithmetic is printed anyway, because that line is the point. **The
    declaration itself is `executor.context_tokens()`**, so this check and a run-card read ONE
    answer; until 2026-09-22 it was a bare `os.environ` read here, and nothing else could see it.
    """
    cap = executor.tool_output_chars()
    rounds, who = _rounds_for_fit(registry)
    # `read_file` caps its OWN output first (`MAX_READ_CHARS`), so a value above that buys no
    # more text - it only spends more of the window. The effective figure is the smaller one.
    effective = MAX_READ_CHARS if cap <= 0 else min(cap, MAX_READ_CHARS)
    label = "unlimited" if cap <= 0 else f"cap {cap} chars"
    note = ("" if cap <= 0 or cap <= MAX_READ_CHARS else
            f"; {cap} is above read_file's own {MAX_READ_CHARS}-char ceiling, which binds first")
    largest, total = _tool_budget_tokens(effective, rounds)
    est = (f"~{largest / 1000:.1f}k in its largest round, ~{total / 1000:.1f}k over the run")
    # **Which budget these figures are for, said out loud.** A role may now declare its own, so the
    # round count is an ASSUMPTION that has to be visible rather than left for the reader to infer.
    budget = "" if who == "the default" else f" ({who} declares {rounds})"
    # **Read from the DECLARATION, not from `os.environ` here.** The same number is recorded on
    # every run-card beside the prompt it was measured against, and two readers of one variable is
    # how the two drift - see `executor.context_tokens`.
    window = executor.context_tokens(declared)
    if not window:
        return "PASS", (f"{label} x {rounds} rounds{budget} = {est} tokens, and the system prompt "
                        f"and the objective are on top of both{note}; declare `context_tokens` in "
                        f"`.solar/config.json` (or SOLAR_CONTEXT_TOKENS) to have the largest round "
                        f"checked against the input window")
    if largest > window:
        return "WARN", (f"{label} x {rounds} rounds{budget} = {est} tokens, and the largest round "
                        f"alone exceeds the declared INPUT window of {window}: the reserve for the "
                        f"ANSWER is gone, and past the served window the server drops the OLDEST "
                        f"tokens silently (system prompt and objective first). Raise the model's "
                        f"num_ctx, then the cap{note}")
    return "PASS", (f"{label} x {rounds} rounds{budget} = {est} tokens, and the largest round fits "
                    f"the declared input window of {window}{note}")


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
        print(f"{mark} {name}: {status}{(' - ' + lines[0]) if lines else ''}")
        for extra in lines[1:]:
            print(f"    {extra}")


def _arm_stdio() -> None:
    """Make output survive a console or a locale that cannot encode it.

    **Read, reproduced 2026-09-20.** When stdout is a pipe or a file, Python uses the
    LOCALE encoding, not the console's - cp1252 on this machine. The status marks this module
    prints (U+2705, U+274C, U+26A0) are not in cp1252, so `solar-governor init | Out-File`
    exited 1 with `UnicodeEncodeError: 'charmap' codec can't encode character U+2705`.
    **Every non-interactive caller hits that**, which is exactly how agents and scripts drive
    this CLI - the engagement's wrapper only survived it by exporting PYTHONIOENCODING=utf-8,
    a workaround on the caller's side for a defect on ours.

    `errors="replace"` and not "strip the marks": a decorative character must never abort a
    command, and on a console that can render them they still render. **The machine interface
    is handled separately** - `_json_out` escapes non-ASCII, so a substituted character can
    never reach the payload.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass  # a replaced or detached stream is the caller's business, not ours


def cmd_policy(args):
    """Print one role's write policy - the consultation layer, with no model in it.

    `agent-tool-surface.md` section 4 measured the gap this closes: the engagement has 42 checks
    that can say **afterwards** that something was wrong and nothing that says beforehand what is
    allowed, so a role discovers four layers of policy one refusal at a time. The answer is
    `Workspace`'s own, ASKED rather than restated - which is what makes it incapable of
    disagreeing with the enforcement it reports.

    `--role` and `--repo` default to `SOLAR_ROLE` and `SOLAR_ROOT`, which the command layer puts
    in the environment of every child it runs. That default is what lets ONE declared command
    answer for whichever role called it, in an `argv` that cannot be parameterised.
    """
    role = (args.role or os.environ.get("SOLAR_ROLE", "")).strip()
    root = Path(args.repo or os.environ.get("SOLAR_ROOT", ".")).expanduser().resolve()
    try:
        cfg = Config.load(_cfg_path(root))
        reg = load_registry(cfg.root / ".solar" / "registry.json")
    except Exception as e:
        print(f"policy: cannot read the install under {root}: {e}", file=sys.stderr)
        sys.exit(EXIT_USAGE)
    if not role:
        print(f"policy: name a role with --role (or SOLAR_ROLE, when a command runs this). "
              f"In the registry: {', '.join(sorted(role_keys(reg)))}", file=sys.stderr)
        sys.exit(EXIT_USAGE)
    spec = reg.get(role) or {}
    if "system" not in spec:
        print(f"policy: no role '{role}' in the registry (have: {role_keys(reg)})",
              file=sys.stderr)
        sys.exit(EXIT_USAGE)

    ws = Workspace(cfg.root, spec)
    report = ws.policy(role)
    if args.path:
        report["path"] = args.path
        report["verdict"] = ws.verdict(args.path)
    if args.json:
        print(json.dumps(report, indent=2))
        return
    print(f"write policy - {report['role']}   (root: {report['root']})")
    print(f"  may write : {'yes' if report['may_write'] else 'NO - every mutating tool refuses'}")
    print(f"  allowed   : {', '.join(report['allowed_prefixes']) or '(nothing)'}")
    print(f"  denied    : {', '.join(report['write_deny']) or '(none declared for this role)'}")
    glob = ', '.join(report["write_glob"]) or '(none declared)'
    if report["write_glob_refused"]:
        glob += f"   [refused as unanchored: {', '.join(report['write_glob_refused'])}]"
    print(f"  glob      : {glob}")
    print(f"  protected : dirs {', '.join(report['protected_dirs'])}")
    print(f"              names {', '.join(report['protected_names'])}")
    if args.path:
        print(f"  verdict   : {report['verdict']}")


def main():
    _arm_stdio()
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
    p_run.add_argument("--clone", default=None,
                       help="which CLONE this run is about (T50): the value a declaration's "
                            "`repos/{clone}` cwd resolves against. Required when the vocabulary "
                            "declares one, and `none` is a legal answer for a run that touches "
                            "no clone — but not for one whose pinned roles hold a "
                            "clone-scoped command.")
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

    p_pol = sub.add_parser("policy", help="print one role's write policy, before any attempt")
    p_pol.add_argument("--repo", default=None,
                       help="the install root (default: SOLAR_ROOT, else .)")
    p_pol.add_argument("--role", default="",
                       help="the role key (default: SOLAR_ROLE, which the command layer passes "
                            "to every child it runs)")
    p_pol.add_argument("--path", default="",
                       help="also answer for ONE path: which layer would refuse it, if any")
    p_pol.add_argument("--json", action="store_true")
    p_pol.set_defaults(fn=cmd_policy)

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
