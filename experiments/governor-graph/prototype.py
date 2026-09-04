"""governor-graph prototype — step 3.1: minimal graph + state.

Seeds the SOLAR governor-as-graph (v5, docs/versions/v5.md). Three nodes over a
TypedDict state; the state schema mirrors v5 §4 (ledger-sourced fields +
runtime fields). Later evals extend this file: conditional edges (3.2),
interrupt (3.3), checkpointer (3.4), streaming (3.5), compactor (3.6),
hub KB MCP call (3.7).
"""
import operator
from typing import Annotated, Literal, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class TaskRow(TypedDict):
    id: str
    task: str
    agent: str
    status: str
    stage: str


class SolarState(TypedDict):
    """v5 §4 state schema (ledger-sourced + runtime fields)."""
    objective: str
    materials_status: str                            # PENDING / READY / INSUFFICIENT
    design_status: str                               # PENDING / APPROVED / REJECTED
    message: str                                     # incoming message (routing input)
    intent: str                                      # routed intent (EVAL 3)
    adversarial_verdict: str                         # approve / deny (EVAL 1)
    rework_count: int                                # Ralph loop counter (EVAL 1)
    work_queue: Annotated[list, operator.add]        # accumulate across nodes
    decisions_log: Annotated[list, operator.add]     # append-only
    stage: str


def material_gate(state: SolarState) -> dict:
    # G1: materials-sufficient (minimal build: objective present == READY)
    status = "READY" if state.get("objective") else "INSUFFICIENT"
    return {
        "materials_status": status,
        "decisions_log": [f"material_gate -> {status}"],
        "stage": "material_gate",
    }


def design_gate(state: SolarState) -> dict:
    # G2: design-approved (full mode interrupts here; minimal build auto-approves)
    status = "APPROVED" if state.get("materials_status") == "READY" else "REJECTED"
    return {"design_status": status, "stage": "design_gate"}


def dispatch(state: SolarState) -> dict:
    row: TaskRow = {
        "id": "T1",
        "task": state.get("objective", ""),
        "agent": "TBD",
        "status": "PENDING",
        "stage": "dispatched",
    }
    return {
        "work_queue": [row],
        "decisions_log": ["dispatch -> T1 queued"],
        "stage": "dispatched",
    }


builder = StateGraph(SolarState)
builder.add_node("material_gate", material_gate)
builder.add_node("design_gate", design_gate)
builder.add_node("dispatch", dispatch)
builder.add_edge(START, "material_gate")
builder.add_edge("material_gate", "design_gate")
builder.add_edge("design_gate", "dispatch")
builder.add_edge("dispatch", END)
graph = builder.compile()

# --- EVAL 3 (step 3.2): conditional edges / deterministic routing ---
# Hub router intents (§13.6): capture / query / propose / publish.
INTENT_KEYWORDS = {
    "capture": ["log", "record", "capture", "remember"],
    "propose": ["propose", "draft", "write"],
    "publish": ["publish", "post", "send"],
}
DEFAULT_INTENT = "query"


def classify(state: SolarState) -> dict:
    """Deterministic keyword intent classifier (no LLM -> provably repeatable)."""
    msg = state.get("message", "").lower()
    for intent, kws in INTENT_KEYWORDS.items():
        if any(k in msg for k in kws):
            return {"intent": intent}
    return {"intent": DEFAULT_INTENT}


def _handler(intent: str):
    def node(state: SolarState) -> dict:
        return {
            "work_queue": [{"id": "Q", "task": state.get("message", ""),
                            "agent": intent, "status": "PENDING", "stage": intent}],
            "decisions_log": [f"route -> {intent}"],
            "stage": intent,
        }
    return node


HANDLERS = {intent: _handler(intent) for intent in ("capture", "query", "propose", "publish")}


def route(state: SolarState) -> str:
    return state.get("intent", DEFAULT_INTENT)


routing = StateGraph(SolarState)
routing.add_node("classify", classify)
for intent, handler in HANDLERS.items():
    routing.add_node(f"handle_{intent}", handler)
routing.add_edge(START, "classify")
routing.add_conditional_edges(
    "classify", route,
    {i: f"handle_{i}" for i in HANDLERS},
)
for intent in HANDLERS:
    routing.add_edge(f"handle_{intent}", END)
routing_graph = routing.compile()

# --- EVAL 1 (step 3.3): interrupt / HITL adversarial gate ---
# Full-mode v5: DESIGN_GATE and ADVERSARIAL are interrupts. This eval proves the
# approve/deny branch + Ralph rework loop with a checkpointer (MemorySaver here;
# SQLite in 3.4 for durable restart-safety).


def implement(state: SolarState) -> dict:
    return {
        "decisions_log": ["implement -> output artifact written"],
        "stage": "implemented",
    }


def adversarial_review(state: SolarState) -> dict:
    # Pauses the graph; the human resumes with Command(resume="approve"|"deny").
    verdict = interrupt({"ask": "Adversarial review: approve or deny the output?"})
    return {"adversarial_verdict": verdict, "stage": "adversarial_review"}


def complete(state: SolarState) -> dict:
    return {"decisions_log": ["TASK_COMPLETE"], "stage": "complete"}


def rework(state: SolarState) -> dict:
    count = state.get("rework_count", 0) + 1
    return {
        "rework_count": count,
        "decisions_log": [f"rework -> attempt {count}"],
        "stage": "rework",
    }


def route_after_review(state: SolarState) -> Literal["complete", "rework"]:
    return "complete" if state.get("adversarial_verdict") == "approve" else "rework"


hitl = StateGraph(SolarState)
hitl.add_node("implement", implement)
hitl.add_node("adversarial_review", adversarial_review)
hitl.add_node("complete", complete)
hitl.add_node("rework", rework)
hitl.add_edge(START, "implement")
hitl.add_edge("implement", "adversarial_review")
hitl.add_conditional_edges(
    "adversarial_review", route_after_review,
    {"complete": "complete", "rework": "rework"},
)
hitl.add_edge("rework", "implement")
hitl.add_edge("complete", END)
hitl_graph = hitl.compile(checkpointer=MemorySaver())


def _paused(st: dict) -> bool:
    return "__interrupt__" in st


if __name__ == "__main__":
    print("== 3.1: objective present (flows through all 3 nodes) ==")
    out = graph.invoke(
        {"objective": "Tailor CV for JD-X", "work_queue": [], "decisions_log": []}
    )
    for k, v in out.items():
        print(f"  {k}: {v}")

    print("\n== EVAL 3: deterministic routing (5 runs each, route must be stable) ==")
    samples = [
        "remember this decision",     # capture
        "how do we do RAG",           # query (default)
        "draft an outreach message",  # propose
        "post to LinkedIn",           # publish
    ]
    for msg in samples:
        routes = []
        for _ in range(5):
            o = routing_graph.invoke({"message": msg, "work_queue": [], "decisions_log": []})
            routes.append(o.get("stage"))
        ok = len(set(routes)) == 1
        print(f"  {msg!r:35} -> {routes[0]:9} deterministic={ok}")

    print("\n== EVAL 1: HITL interrupt (approve vs deny branch) ==")
    # approve path
    cfg1 = {"configurable": {"thread_id": "eval1-approve"}}
    r1 = hitl_graph.invoke({"objective": "x", "work_queue": [], "decisions_log": []}, cfg1)
    print(f"  run1 paused: {_paused(r1)}  interrupt={r1['__interrupt__'][0].value}")
    r1b = hitl_graph.invoke(Command(resume="approve"), cfg1)
    print(f"  approve -> stage={r1b['stage']} paused={_paused(r1b)} rework={r1b.get('rework_count', 0)}")

    # deny path -> rework -> pause again -> approve -> complete
    cfg2 = {"configurable": {"thread_id": "eval1-deny"}}
    r2 = hitl_graph.invoke({"objective": "x", "work_queue": [], "decisions_log": []}, cfg2)
    r2b = hitl_graph.invoke(Command(resume="deny"), cfg2)
    print(f"  deny -> stage={r2b.get('stage')} paused={_paused(r2b)} rework={r2b.get('rework_count', 0)}")
    r2c = hitl_graph.invoke(Command(resume="approve"), cfg2)
    print(f"  then approve -> stage={r2c.get('stage')} paused={_paused(r2c)} rework={r2c.get('rework_count', 0)}")

    ok1 = r1b.get("stage") == "complete" and not _paused(r1b)
    ok2 = r2b.get("rework_count", 0) == 1 and _paused(r2b)
    ok3 = r2c.get("stage") == "complete" and not _paused(r2c)
    print(f"  RESULT: approve->complete={ok1}  deny->rework&repause={ok2}  deny-then-approve->complete={ok3}")
