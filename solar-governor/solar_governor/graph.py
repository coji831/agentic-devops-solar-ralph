"""Graph (v5 §5): build the profile graph + run a task end-to-end.

Light profile (default): MATERIAL_GATE -> DISPATCH -> SPECIALIST -> REVIEW
(conditional) -> COMPLETE, with a bounded rework loop (<=3 attempts). Full
profile adds design-gate interrupt + compactor + adversarial (later).
"""
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from . import executor
from .core import Config, SolarState
from .registry import chain_entry, chain_text, load as load_registry, role_keys

MAX_ATTEMPTS = 3

# keyword -> role hints, applied against the LOADED registry (repo roles win if
# their name/description matches; generic defaults remain as fallback)
_ROLE_HINTS = {
    "implementer": ("implement", "refactor", "build", "feature", "code", "fix"),
    "tester": ("test", "spec", "coverage", "verify"),
    "reviewer": ("review", "audit", "check"),
}


def _registry_role_hint(task: str, registry: dict) -> str | None:
    """Prefer a repo-specific role whose name appears in the task (deterministic)."""
    low = (task or "").lower()
    # repo roles = registry minus generic defaults and structural keys
    generic = set(_ROLE_HINTS)
    for role, spec in registry.items():
        # a real role spec carries a `system` prompt; playbook/chain entries do not
        if role in generic or not isinstance(spec, dict) or "system" not in spec:
            continue
        name = str(spec.get("role", role)).lower()
        if name.replace(" ", "-") in low or name.split()[-1] in low or role.replace("_", "-") in low:
            return role
    return None


def _classify(task: str, registry: dict | None = None) -> str:
    reg = registry or {}
    hit = _registry_role_hint(task, reg)
    if hit:
        return hit
    low = (task or "").lower()
    # priority order breaks keyword-count ties: "add tests to X" -> tester,
    # even though "feature/build" are also present.
    best, best_score = "implementer", 0
    for role in ("tester", "reviewer", "implementer"):
        score = sum(low.count(k) for k in _ROLE_HINTS[role])
        if score > best_score:
            best, best_score = role, score
    return best


def _role_spec(cfg: Config, role: str) -> dict:
    """Return a role's FULL registry spec (repo-specific role wins).

    The whole entry is returned, not just the prompt: the workspace tool layer
    needs the role's declared `tools` — and, once the deny-list lands, its
    `write_scope`/`write_deny` — to decide what the role may be OFFERED and
    where it may write. An unknown role yields {} so callers fall back to a
    generic prompt instead of raising.
    """
    reg = load_registry(cfg.root / ".solar" / "registry.json")
    return reg.get(role) or {}


def _role_prompt(spec: dict, role: str) -> str:
    """The role's system prompt, or a generic one when the registry has none."""
    return spec.get("system", f"You are the {role} specialist.")


def _chain_note(cfg: Config, chain_name: str) -> str:
    """Human-readable chain block for a handoff ('' when not a chain run)."""
    if not chain_name:
        return ""
    cm = (load_registry(cfg.root / ".solar" / "registry.json").get("chains") or {})
    if chain_name not in cm:
        return ""
    return f"chain `{chain_name}`: {chain_text(cm, chain_name)}"


def _execute(cfg: Config, state: SolarState) -> dict:
    """Run the routed specialist role through the HTTP/stub runner.

    System prompt comes from the loaded registry (repo-specific role wins), and
    the WHOLE role spec is passed on so the workspace tool layer can derive its
    policy from the role. The executor falls back to a stub when no API key is
    present (cfg.model "" or SOLAR_API_KEY unset), so the graph stays testable
    without credentials.
    """
    role = state.get("role", "implementer")
    spec = _role_spec(cfg, role)
    objective = state.get("objective", "")
    res = executor.run(role=role, system_prompt=_role_prompt(spec, role),
                       objective=objective, repo=cfg.root, cfg_model=cfg.model,
                       spec=spec, human_approval=cfg.human_approval,
                       cfg_reasoning=cfg.reasoning_effort, cfg_tier=cfg.model_tier)
    return {
        "output": res.get("output", ""),
        "model": res.get("model", "stub"),
        "tokens_in": res.get("usage", {}).get("in", 0),
        "tokens_out": res.get("usage", {}).get("out", 0),
        "tool_calls": res.get("tool_calls", 0),
        "error": res.get("error") or "",
        "forced_final": bool(res.get("forced_final", False)),
    }


def _dispatch_agent(cfg: Config, state: SolarState, attempts: int) -> dict:
    """AgentDispatchRunner: write a handoff, then HITL-interrupt for the result.

    The human runs the matching .agent.md specialist in VS Code Copilot (DeepSeek
    via the extension) and pastes the result (or a result-file path) to resume.
    A dispatch is always ONE link of work: if the run is part of a named chain
    the handoff only carries neutral chain context (the coordinator runs the
    links) — it never tells the agent to run the rest of the chain itself.
    """
    role = state.get("role", "implementer")
    spec = _role_spec(cfg, role)
    chain_note = _chain_note(cfg, state.get("chain", ""))
    handoff = executor.write_handoff(role=role, system_prompt=_role_prompt(spec, role),
                                     objective=state.get("objective", ""),
                                     repo=cfg.root, cfg_model=cfg.model,
                                     attempt=attempts, chain_note=chain_note,
                                     role_model=spec.get("model", ""))
    resumed = interrupt({"kind": "agent-dispatch",
                         "role": role,
                         "attempt": attempts,
                         "chain": state.get("chain", ""),
                         "handoff": str(handoff),
                         "ask": (f"Run the `{role}` agent in VS Code Copilot "
                                 f"(handoff: {handoff.name}), then paste its final "
                                 f"result or the result-file path:")})
    output = executor.resolve_result(resumed, cfg.root)
    return {"attempts": attempts, "output": output, "model": f"agent-dispatch:{role}",
            "stage": "specialist",
            "decisions_log": [f"specialist attempt {attempts} (agent-dispatch: {role})"]}


def build_nodes(cfg: Config):
    def material_gate(state: SolarState) -> dict:
        status = "READY" if state.get("objective") else "INSUFFICIENT"
        return {"materials_status": status, "stage": "material_gate",
                "decisions_log": [f"material_gate -> {status}"]}

    def dispatch(state: SolarState) -> dict:
        reg = load_registry(cfg.root / ".solar" / "registry.json")
        chain_name = state.get("chain") or ""
        pinned = state.get("role") or ""
        role = None
        if chain_name:
            cm = reg.get("chains") or {}
            if chain_name in cm:
                role = chain_entry(cm, chain_name)
        if role is None and pinned and pinned in role_keys(reg):
            role = pinned                       # --role: pin dispatch (Hermes decision)
        if role is None:
            role = _classify(state.get("objective", ""), reg)
        return {"role": role, "chain": chain_name, "stage": "dispatched",
                "work_queue": [{"id": "T1", "task": state.get("objective", ""),
                                "role": role, "status": "PENDING", "stage": "dispatched"}],
                "decisions_log": [f"dispatch -> {role}" + (f" (chain {chain_name})" if chain_name else "")]}

    def specialist(state: SolarState) -> dict:
        attempts = state.get("attempts", 0) + 1
        runner = executor.select_runner(cfg.runner)
        if runner == "agent-dispatch":
            return _dispatch_agent(cfg, state, attempts)
        result = _execute(cfg, state)
        return {"attempts": attempts, "stage": "specialist",
                "decisions_log": [f"specialist attempt {attempts}"], **result}

    def review(state: SolarState) -> dict:
        # Never auto-approve an executor failure: an error output must not read
        # as success (the harness exists to stop false "done"). Terminal, no rework.
        if state.get("error"):
            return {"verdict": "REJECTED", "stage": "review",
                    "decisions_log": [f"review -> REJECTED (executor error: "
                                      f"{str(state['error'])[:80]} — no auto-approve)"]}
        if cfg.human_approval:
            verdict = interrupt({"ask": f"Review {state.get('role', 'work')}: approve or deny?"})
        else:
            verdict = "approve"
        return {"verdict": "APPROVED" if verdict == "approve" else "REJECTED", "stage": "review"}

    def route(state: SolarState) -> str:
        if state.get("error"):                    # executor failure is terminal
            return "complete"
        if state.get("verdict") == "APPROVED" or state.get("attempts", 1) >= MAX_ATTEMPTS:
            return "complete"
        return "specialist"

    def complete(state: SolarState) -> dict:
        return {"stage": "complete", "decisions_log": ["TASK_COMPLETE"]}

    return locals()


def build_graph(cfg: Config):
    n = build_nodes(cfg)
    b = StateGraph(SolarState)
    for name in ("material_gate", "dispatch", "specialist", "review", "complete"):
        b.add_node(name, n[name])
    b.add_edge(START, "material_gate")
    b.add_edge("material_gate", "dispatch")
    b.add_edge("dispatch", "specialist")
    b.add_edge("specialist", "review")
    b.add_conditional_edges("review", n["route"], {"complete": "complete", "specialist": "specialist"})
    b.add_edge("complete", END)
    return b


def initial_state(task: str, chain: str = "", role: str = "") -> dict:
    """v5 §4: initial channel values for a light-profile run."""
    return {"objective": task, "chain": chain, "role": role, "work_queue": [],
            "decisions_log": [], "materials_status": "PENDING", "stage": "start",
            "attempts": 0}


def run_step(cfg: Config, task: str, thread: str | None = None,
             resume: str | None = None, chain: str = "", role: str = "") -> dict:
    """Execute exactly ONE graph step on a thread (SQLite checkpoint).

    - resume=None  -> fresh start for a new thread (optionally as a named chain,
        or pinned to a specific role via `role`).
    - resume=<str> -> resume the thread's pending interrupt with that value
        (agent-dispatch: result text or result-file path; review:
        'approve'|'deny').

    Returns the merged state. A pending interrupt appears under '__interrupt__';
    run_step never prompts on stdin, so callers (human CLI, an agent driver,
    tests) decide how to answer interrupts.
    """
    thread = thread or "t1"
    config = {"configurable": {"thread_id": thread}}
    cfg.root.mkdir(parents=True, exist_ok=True)
    cfg.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    with SqliteSaver.from_conn_string(str(cfg.checkpoint_path)) as cp:
        graph = build_graph(cfg).compile(checkpointer=cp)
        if resume is not None:
            return graph.invoke(Command(resume=resume), config)
        return graph.invoke(initial_state(task, chain=chain, role=role), config)


def pending_interrupt(cfg: Config, thread: str | None = None) -> dict | None:
    """Return the payload dict of the thread's pending interrupt, else None.

    Lets a caller distinguish 'new thread' from 'thread paused at an interrupt'
    so a plain invoke is never used to (incorrectly) resume a paused run.
    """
    thread = thread or "t1"
    config = {"configurable": {"thread_id": thread}}
    with SqliteSaver.from_conn_string(str(cfg.checkpoint_path)) as cp:
        graph = build_graph(cfg).compile(checkpointer=cp)
        try:
            snap = graph.get_state(config)
        except Exception:
            return None
        ints = getattr(snap, "interrupts", ())
        if ints:
            return ints[0].value
    return None


def run_task(cfg: Config, task: str, thread: str | None = None,
             approve: str | None = None, resume_result: str | None = None,
             chain: str = "", role: str = "") -> dict:
    """Interactive/one-shot runner: loop run_step until complete.

    Answers each interrupt on stdin when no value was supplied (kept for the
    human CLI + tests). The --json agent contract uses run_step +
    pending_interrupt directly and never blocks on stdin.

    Interrupt kinds:
      - agent-dispatch: paste the specialist result (or a result-file path).
        `resume_result` supplies it non-interactively (tests/CI).
      - review (human_approval): answered via `approve` ('approve'|'deny').
    """
    thread = thread or "t1"
    result = run_step(cfg, task, thread, chain=chain, role=role)
    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        kind = payload.get("kind", "review")
        if kind == "agent-dispatch":
            print(f"\n🧭 AGENT DISPATCH — {payload.get('ask', '')}")
            if resume_result is None:
                resume_result = input("   result (paste text or result-file path): ").strip()
            result = run_step(cfg, task, thread, resume=resume_result)
            resume_result = None          # one-shot: a rework attempt re-prompts
            continue
        question = payload.get("ask", "approve or deny?")
        if approve is None:
            approve = input(f"{question} [approve/deny]: ").strip().lower()
        verdict = "approve" if approve == "approve" else "deny"
        result = run_step(cfg, task, thread, resume=verdict)
        approve = None                    # one-shot
    return result
