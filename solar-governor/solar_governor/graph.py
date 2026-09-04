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
from .registry import load as load_registry

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
    # repo roles = registry minus generic defaults
    generic = set(_ROLE_HINTS)
    for role, spec in registry.items():
        if role in generic:
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


def _role_spec(cfg: Config, role: str) -> tuple[str, str]:
    """Return (role, system_prompt) from the loaded registry (repo wins)."""
    reg = load_registry(cfg.root / ".solar" / "registry.json")
    spec = reg.get(role, {})
    return role, spec.get("system", f"You are the {role} specialist.")


def _execute(cfg: Config, state: SolarState) -> dict:
    """Run the routed specialist role through the HTTP/stub runner.

    System prompt comes from the loaded registry (repo-specific role wins). The
    executor falls back to a stub when no API key is present (cfg.model "" or
    SOLAR_API_KEY unset), so the graph stays testable without credentials.
    """
    role, system = _role_spec(cfg, state.get("role", "implementer"))
    objective = state.get("objective", "")
    res = executor.run(role=role, system_prompt=system, objective=objective,
                       repo=cfg.root, cfg_model=cfg.model)
    return {
        "output": res.get("output", ""),
        "model": res.get("model", "stub"),
        "tokens_in": res.get("usage", {}).get("in", 0),
        "tokens_out": res.get("usage", {}).get("out", 0),
        "tool_calls": res.get("tool_calls", 0),
        "error": res.get("error") or "",
    }


def _dispatch_agent(cfg: Config, state: SolarState, attempts: int) -> dict:
    """AgentDispatchRunner: write a handoff, then HITL-interrupt for the result.

    The human runs the matching .agent.md specialist in VS Code Copilot (DeepSeek
    via the extension) and pastes the result (or a result-file path) to resume.
    """
    role, system = _role_spec(cfg, state.get("role", "implementer"))
    handoff = executor.write_handoff(role=role, system_prompt=system,
                                     objective=state.get("objective", ""),
                                     repo=cfg.root, cfg_model=cfg.model,
                                     attempt=attempts)
    resumed = interrupt({"kind": "agent-dispatch",
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
        role = _classify(state.get("objective", ""), reg)
        return {"role": role, "stage": "dispatched",
                "work_queue": [{"id": "T1", "task": state.get("objective", ""),
                                "role": role, "status": "PENDING", "stage": "dispatched"}],
                "decisions_log": [f"dispatch -> {role}"]}

    def specialist(state: SolarState) -> dict:
        attempts = state.get("attempts", 0) + 1
        runner = executor.select_runner(cfg.runner)
        if runner == "agent-dispatch":
            return _dispatch_agent(cfg, state, attempts)
        result = _execute(cfg, state)
        return {"attempts": attempts, "stage": "specialist",
                "decisions_log": [f"specialist attempt {attempts}"], **result}

    def review(state: SolarState) -> dict:
        if cfg.human_approval:
            verdict = interrupt({"ask": f"Review {state.get('role', 'work')}: approve or deny?"})
        else:
            verdict = "approve"
        return {"verdict": "APPROVED" if verdict == "approve" else "REJECTED", "stage": "review"}

    def route(state: SolarState) -> str:
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


def run_task(cfg: Config, task: str, thread: str | None = None,
             approve: str | None = None, resume_result: str | None = None) -> dict:
    """Run a task under the profile's graph with a SQLite checkpoint.

    Returns the final state. Interrupt kinds:
      - agent-dispatch: the human runs the .agent.md specialist in the IDE and
        pastes the result (or a result-file path). Use `resume_result` to supply
        it non-interactively (tests/CI); otherwise a CLI prompt reads it.
      - review (human_approval): answered via `approve` ('approve'|'deny') or a
        CLI prompt when None.
    """
    thread = thread or "t1"
    config = {"configurable": {"thread_id": thread}}
    initial: dict = {"objective": task, "work_queue": [], "decisions_log": [],
                     "materials_status": "PENDING", "stage": "start", "attempts": 0}
    cfg.root.mkdir(parents=True, exist_ok=True)
    cfg.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    with SqliteSaver.from_conn_string(str(cfg.checkpoint_path)) as cp:
        graph = build_graph(cfg).compile(checkpointer=cp)
        result = graph.invoke(initial, config)
        while "__interrupt__" in result:
            payload = result["__interrupt__"][0].value
            kind = payload.get("kind", "review")
            if kind == "agent-dispatch":
                print(f"\n🧭 AGENT DISPATCH — {payload.get('ask', '')}")
                if resume_result is None:
                    resume_result = input("   result (paste text or result-file path): ").strip()
                result = graph.invoke(Command(resume=resume_result), config)
                continue
            question = payload.get("ask", "approve or deny?")
            verdict = approve
            if verdict not in ("approve", "deny"):
                verdict = input(f"{question} [approve/deny]: ").strip().lower()
            result = graph.invoke(Command(resume=verdict), config)
    return result
