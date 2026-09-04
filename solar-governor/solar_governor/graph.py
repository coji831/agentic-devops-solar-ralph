"""Graph (v5 §5): build the profile graph + run a task end-to-end.

Light profile (default): MATERIAL_GATE -> DISPATCH -> SPECIALIST -> REVIEW
(conditional) -> COMPLETE, with a bounded rework loop (<=3 attempts). Full
profile adds design-gate interrupt + compactor + adversarial (later).
"""
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from .core import Config, SolarState
from .registry import load as load_registry

MAX_ATTEMPTS = 3


def _classify(task: str) -> str:
    low = (task or "").lower()
    if any(k in low for k in ("test", "spec", "coverage", "verify")):
        return "tester"
    return "implementer"


def _execute(cfg: Config, state: SolarState) -> str:
    """Run the specialist for the routed role.

    cfg.model == "" -> deterministic stub executor (no API key). A real model
    executor plugs in here (workspace MCP + LLM client) when cfg.model is set.
    """
    role = state.get("role", "implementer")
    if not cfg.model:
        return (f"[{role}] plan for: {state.get('objective', '')}\n"
                f"  - PREMISE_GATE: verify the request vs ground truth\n"
                f"  - implement the minimal change\n"
                f"  - self-check + tests")
    # TODO(model executor): call the model with the role system prompt + tools.
    # Requires a workspace MCP server + a provider key. Falls back to stub for now.
    return (f"[{role}] MODEL EXECUTION NOT YET WIRED (cfg.model={cfg.model!r}); "
            f"returning stub plan. Add the LLM client + workspace tool in graph.py._execute.")


def build_nodes(cfg: Config):
    def material_gate(state: SolarState) -> dict:
        status = "READY" if state.get("objective") else "INSUFFICIENT"
        return {"materials_status": status, "stage": "material_gate",
                "decisions_log": [f"material_gate -> {status}"]}

    def dispatch(state: SolarState) -> dict:
        role = _classify(state.get("objective", ""))
        return {"role": role, "stage": "dispatched",
                "work_queue": [{"id": "T1", "task": state.get("objective", ""),
                                "role": role, "status": "PENDING", "stage": "dispatched"}],
                "decisions_log": [f"dispatch -> {role}"]}

    def specialist(state: SolarState) -> dict:
        attempts = state.get("attempts", 0) + 1
        return {"attempts": attempts, "output": _execute(cfg, state), "stage": "specialist",
                "decisions_log": [f"specialist attempt {attempts}"]}

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


def run_task(cfg: Config, task: str, thread: str | None = None, approve: str | None = None) -> dict:
    """Run a task under the profile's graph with a SQLite checkpoint.

    Returns the final state. Interrupts (human_approval) are answered via the
    `approve` param ('approve'|'deny') or a CLI prompt when None.
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
            question = result["__interrupt__"][0].value.get("ask", "approve or deny?")
            verdict = approve
            if verdict not in ("approve", "deny"):
                verdict = input(f"{question} [approve/deny]: ").strip().lower()
            result = graph.invoke(Command(resume=verdict), config)
    return result
