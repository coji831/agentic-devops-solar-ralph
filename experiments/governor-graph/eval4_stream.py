"""EVAL 4 (step 3.5): streaming — node outputs as they happen.

Streams a multi-node graph to stdout using stream_mode="updates" (each node's
update arrives as it completes), framed like SSE (event:/data:) so the pattern
maps directly to a channel gateway (R9: Slack/WhatsApp later).

Usage:
    python eval4_stream.py
"""
import asyncio
import operator
import time
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    task: str
    log: Annotated[list, operator.add]


def gate(state):
    time.sleep(0.2)
    return {"log": ["gate: materials READY"]}


def plan(state):
    time.sleep(0.2)
    return {"log": ["plan: design approved"]}


def implement(state):
    time.sleep(0.2)
    return {"log": ["implement: artifact written"]}


def review(state):
    time.sleep(0.2)
    return {"log": ["review: APPROVED"]}


def build():
    b = StateGraph(State)
    b.add_node("gate", gate)
    b.add_node("plan", plan)
    b.add_node("implement", implement)
    b.add_node("review", review)
    b.add_edge(START, "gate")
    b.add_edge("gate", "plan")
    b.add_edge("plan", "implement")
    b.add_edge("implement", "review")
    b.add_edge("review", END)
    return b.compile()


def sse(chunk_type: str, data: dict) -> None:
    # minimal SSE-style framing (maps to R9 channel gateway later)
    print(f"event: {chunk_type}")
    print(f"data: {data}")
    print()


async def main():
    graph = build()
    print("== EVAL 4: streaming (stream_mode='updates', SSE-style) ==")
    async for chunk in graph.astream(
        {"task": "ship feature", "log": []}, stream_mode="updates"
    ):
        for node, update in chunk.items():
            sse(node, update)

    print("== done — all node outputs arrived incrementally ==")


if __name__ == "__main__":
    asyncio.run(main())
