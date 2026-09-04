"""solar-governor CLI: init | run | doctor (v5 §9 install surface)."""
import argparse
import json
import sys
import time
from pathlib import Path

from . import executor, runcard
from .core import Config
from .graph import build_graph, run_task
from .ledger import render
from .registry import load as load_registry


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
                           "\n.solar/state/\n.solar/ledger.md\n.solar/runs/\n.solar/handoffs/\n",
                           encoding="utf-8")
    print(f"✅ initialised solar-governor (profile={cfg.profile}, runner={cfg.runner or 'auto'}) in {root}")
    print(f"   config: {_cfg_path(root).relative_to(root)}")
    print(f"   next: solar-governor run \"<task>\"  |  solar-governor doctor")


def cmd_run(args):
    cfg = Config.load(_cfg_path(Path(args.repo).expanduser().resolve()))
    runner = executor.select_runner(cfg.runner)
    started = time.time()
    state = run_task(cfg, args.task, thread=args.thread, approve=args.approve,
                     resume_result=args.result)
    ledger = render(cfg, state)
    card = runcard.write(cfg, state, args.thread or "t1", started)
    print(f"✅ run complete — stage={state.get('stage')} verdict={state.get('verdict')} "
          f"role={state.get('role')} runner={runner}")
    print(f"   model={state.get('model')} tokens: in={state.get('tokens_in',0)} "
          f"out={state.get('tokens_out',0)} tool_calls={state.get('tool_calls',0)}")
    out = state.get("output", "")
    print(f"   output:\n{out}")
    print(f"   ledger: {ledger}")
    print(f"   run-card: {card}")


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
        checks["registry"] = ("PASS", f"{len(reg)} specialists")
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
    p_run.add_argument("--approve", choices=["approve", "deny"], default=None)
    p_run.add_argument("--result", default=None,
                       help="agent-dispatch: supply the agent result text/path non-interactively")
    p_run.set_defaults(fn=cmd_run)

    p_doct = sub.add_parser("doctor", help="install self-check")
    p_doct.add_argument("--repo", default=".")
    p_doct.add_argument("--json", action="store_true")
    p_doct.set_defaults(fn=cmd_doctor)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
