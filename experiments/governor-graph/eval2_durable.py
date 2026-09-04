"""EVAL 2 (step 3.4): checkpointer / durable execution (SQLite).

Proves restart-safety: `phase=write` runs a graph to a mid-point interrupt, then
"loses the session" (exits WITHOUT resuming). A FRESH process (`phase=resume`)
re-creates the graph over the SAME sqlite checkpoint file and resumes exactly
where it stopped.

Usage (two separate processes):
    python eval2_durable.py write
    python eval2_durable.py resume
"""
import operator
import sys
from pathlib import Path
from typing import Annotated, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

DB = Path(__file__).parent / "checkpoints.sqlite"
THREAD = {"configurable": {"thread_id": "eval2-t1"}}


class State(TypedDict):
    task: str
    step: int
    log: Annotated[list, operator.add]


def step1(state): return {"step": 1, "log": ["step1 done"]}
def step2(state):
    verdict = interrupt({"ask": "continue past step 2?"})
    return {"step": 2, "log": [f"step2 continued ({verdict})"]}
def step3(state): return {"step": 3, "log": ["step3 done"]}


def _build(cp):
    b = StateGraph(State)
    b.add_node("step1", step1)
    b.add_node("step2", step2)
    b.add_node("step3", step3)
    b.add_edge(START, "step1")
    b.add_edge("step1", "step2")
    b.add_edge("step2", "step3")
    b.add_edge("step3", END)
    return b.compile(checkpointer=cp)


def phase_write():
    if DB.exists():
        DB.unlink()
    with SqliteSaver.from_conn_string(str(DB)) as cp:
        graph = _build(cp)
        out = graph.invoke({"task": "durable task", "step": 0, "log": []}, THREAD)
        assert "__interrupt__" in out, "expected to pause at step2"
        print("phase=write : paused at step2 ->", out["__interrupt__"][0].value)
        print("phase=write : state so far -> step =", out.get("step"), "| log =", out.get("log"))
    print("phase=write : exiting WITHOUT resume (simulated session loss)")
    return 0


def phase_resume():
    with SqliteSaver.from_conn_string(str(DB)) as cp:
        graph = _build(cp)  # brand-new graph instance, same sqlite file
        out = graph.invoke(Command(resume="yes"), THREAD)
        print("phase=resume: final -> step =", out.get("step"), "| log =", out.get("log"))
        ok = (
            out.get("step") == 3
            and out.get("log") == ["step1 done", "step2 continued (yes)", "step3 done"]
        )
        print("phase=resume:", "PASS — resumed exactly where it stopped" if ok else "FAIL")
        return 0 if ok else 1


if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else "write"
    raise SystemExit({"write": phase_write, "resume": phase_resume}[phase]())
