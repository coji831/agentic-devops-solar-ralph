"""solar-governor CLI: init | run | doctor (v5 §9 install surface)."""
import argparse
import json
import sys
import time
from pathlib import Path

from . import bench, chain, executor, runcard, server
from .core import Config
from .graph import build_graph, pending_interrupt, run_step, run_task
from .ledger import render
from .registry import chains as load_chains
from .registry import load as load_registry
from .registry import role_keys

# exit codes for the --json step contract (agent wrapper drives on these)
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_AGENT_DISPATCH = 10   # paused: run the specialist, resume with --result
EXIT_REVIEW = 11           # paused: ask the human, resume with --approve


def _cfg_path(root: Path) -> Path:
    return root / ".solar" / "config.json"


def cmd_init(args):
    root = Path(args.repo).expanduser().resolve()
    cfg = Config(profile=args.profile, repo=str(root), human_approval=args.approval,
                 runner=args.runner or "")
    solar = root / ".solar"
    (solar / "state").mkdir(parents=True, exist_ok=True)
    cfg.save(_cfg_path(root))
    reg_path = solar / "registry.json"
    if not reg_path.exists():
        reg_path.write_text(json.dumps(load_registry(None), indent=2), encoding="utf-8")
    git = root / ".gitignore"
    if git.exists():
        text = git.read_text(encoding="utf-8")
        if ".solar/state" not in text:
            git.write_text(text.rstrip() +
                           "\n.solar/state/\n.solar/ledger.md\n.solar/runs/\n.solar/handoffs/\n.solar/chains/\n",
                           encoding="utf-8")
    print(f"✅ initialised solar-governor (profile={cfg.profile}, runner={cfg.runner or 'auto'}) in {root}")
    print(f"   config: {_cfg_path(root).relative_to(root)}")
    print(f"   next: solar-governor run \"<task>\"  |  solar-governor doctor")


def cmd_run(args):
    cfg = Config.load(_cfg_path(Path(args.repo).expanduser().resolve()))
    thread = args.thread or "t1"
    started = time.time()
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
        if getattr(args, "auto", False):
            return _cmd_run_chain_auto(cfg, args, thread)
    if args.json:
        return _cmd_run_json(cfg, args, thread, started)
    # interactive/one-shot path (stdin prompts at interrupts)
    state = run_task(cfg, args.task, thread=thread, approve=args.approve,
                     resume_result=args.result, chain=args.chain or "",
                     role=args.role or "")
    _write_artifacts(cfg, state, thread, started)
    runner = executor.select_runner(cfg.runner)
    chain = f" chain={state.get('chain')}" if state.get("chain") else ""
    print(f"✅ run complete — stage={state.get('stage')} verdict={state.get('verdict')} "
          f"role={state.get('role')}{chain} runner={runner}")
    print(f"   model={state.get('model')} tokens: in={state.get('tokens_in',0)} "
          f"out={state.get('tokens_out',0)} tool_calls={state.get('tool_calls',0)}")
    out = state.get("output", "")
    print(f"   output:\n{out}")
    print(f"   ledger: {cfg.ledger_path}")
    print(f"   run-card: {cfg.root / '.solar' / 'runs' / f'{thread}.json'}")


def _cmd_run_chain_auto(cfg, args, thread) -> None:
    """Headless auto-chain: run the whole named chain link-by-link (http/stub)."""
    agg = chain.run_chain(cfg, args.chain, args.task, thread=thread)
    chain.print_chain(agg)


def _write_artifacts(cfg, state, thread, started) -> None:
    """Render the human-view ledger + run-card from a state snapshot.

    Called at every --json step so progress is on disk even when the run is
    paused at an interrupt; the final step overwrites the run-card.
    """
    render(cfg, state)
    runcard.write(cfg, state, thread, started)


def _state_summary(state: dict) -> dict:
    return {k: state.get(k) for k in
            ("objective", "role", "materials_status", "stage", "verdict",
             "attempts", "tokens_in", "tokens_out", "tool_calls", "error")}


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
               "output": state.get("output", ""),
               "ledger": str(cfg.ledger_path),
               "run_card": str(cfg.root / ".solar" / "runs" / f"{thread}.json"),
               "state": _state_summary(state)}, EXIT_OK)


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
    checks["checkpoint-writable"] = ("PASS" if cfg.checkpoint_path.parent.exists() else "FAIL", "")
    try:
        build_graph(cfg)
        checks["graph-compiles"] = ("PASS", "")
    except Exception as e:
        checks["graph-compiles"] = ("FAIL", str(e))
    try:
        reg = load_registry(root / ".solar" / "registry.json")
        n_roles = len(role_keys(reg))
        cm = load_chains(root / ".solar" / "registry.json")
        detail = f"{n_roles} specialists" + (f", chains: {sorted(cm)}" if cm else "")
        checks["registry"] = ("PASS", detail)
    except Exception as e:
        checks["registry"] = ("FAIL", str(e))
    runner = executor.select_runner(cfg.runner)
    detail = {"agent-dispatch": "hand off to .agent.md agents in the IDE",
              "http": "OpenAI-compatible (SOLAR_API_KEY set)",
              "stub": "no API key -> deterministic stub"}[runner]
    checks["runner"] = ("PASS", f"{runner} ({detail})")
    if args.json:
        print(json.dumps({k: {"status": v[0], "detail": v[1]} for k, v in checks.items()}, indent=2))
        return
    _print_doctor(checks)
    sys.exit(0 if all(v[0] == "PASS" for v in checks.values()) else 1)


def _print_doctor(checks: dict[str, tuple]) -> None:
    for name, (status, detail) in checks.items():
        mark = "✅" if status == "PASS" else "❌"
        print(f"{mark} {name}: {status}{(' - ' + str(detail)) if detail else ''}")


def main():
    ap = argparse.ArgumentParser(prog="solar-governor", description="SOLAR-Ralph v5 runtime")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="initialise .solar config + registry")
    p_init.add_argument("--repo", default=".")
    p_init.add_argument("--profile", choices=["light", "full"], default="light")
    p_init.add_argument("--approval", action="store_true", help="human_approval on (review interrupt)")
    p_init.add_argument("--runner", choices=["agent-dispatch", "http", "stub", ""], default="",
                        help="how specialists execute (default auto: http if key else stub)")
    p_init.set_defaults(fn=cmd_init)

    p_run = sub.add_parser("run", help="run a task through the graph")
    p_run.add_argument("task")
    p_run.add_argument("--repo", default=".")
    p_run.add_argument("--thread", default=None)
    p_run.add_argument("--chain", default=None,
                       help="run a named chain from the registry: dispatch the chain "
                            "entry; it runs the whole chain itself (handoff marks it "
                            "CHAIN ENTRY). With --auto: run the whole chain headless.")
    p_run.add_argument("--auto", action="store_true",
                       help="with --chain: run every link headless in order (http/stub, "
                            "one run-card per link) instead of dispatching only the entry")
    p_run.add_argument("--role", default=None,
                       help="pin dispatch to one registry role (skip keyword classify) — "
                            "e.g. a Hermes intake decision")
    p_run.add_argument("--approve", choices=["approve", "deny"], default=None)
    p_run.add_argument("--result", default=None,
                       help="agent-dispatch: supply the agent result text/path non-interactively")
    p_run.add_argument("--json", action="store_true",
                       help="one graph step, machine-readable (exit 0 complete · "
                            "10 agent-dispatch · 11 review · 2 error)")
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

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
