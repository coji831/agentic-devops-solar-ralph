"""EVAL 6 (step 3.6): compactor node — token-cost + context hygiene.

A specialist's raw output collapses into a compact digest; the NEXT node
receives ONLY the digest (channel isolation: the consumer graph's input schema
has just `digest`, so `raw` is unreachable); the token delta is measured.
In production the compactor is an LLM node; here a deterministic heuristic
keeps the eval repeatable.

Usage:
    python eval6_compactor.py
"""
import re
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

RAW = "Specialist output. " * 60          # ~120 tokens of raw simulated output


def count_tokens(text: str) -> int:
    return len(text.split())


def compress(raw: str, max_words: int = 45) -> str:
    """Deterministic compactor: keep leading sentences up to a word budget."""
    sentences = re.split(r"(?<=[.!?]) +", raw.strip())
    out, words = [], 0
    for s in sentences:
        n = count_tokens(s)
        if words + n > max_words:
            break
        out.append(s)
        words += n
    return " ".join(out)


class CompactorState(TypedDict):
    raw: str
    digest: str


def compactor(state: CompactorState) -> dict:
    return {"digest": compress(state["raw"])}


compactor_graph = (
    StateGraph(CompactorState)
    .add_node("compactor", compactor)
    .add_edge(START, "compactor")
    .add_edge("compactor", END)
    .compile()
)


class ConsumerState(TypedDict):
    digest: str          # ONLY this channel — raw is unreachable here
    ack: str


def consumer(state: ConsumerState) -> dict:
    return {"ack": f"consumer used digest ({count_tokens(state['digest'])} tokens)"}


consumer_graph = (
    StateGraph(ConsumerState)
    .add_node("consumer", consumer)
    .add_edge(START, "consumer")
    .add_edge("consumer", END)
    .compile()
)


if __name__ == "__main__":
    raw_tokens = count_tokens(RAW)
    digest = compactor_graph.invoke({"raw": RAW})["digest"]
    digest_tokens = count_tokens(digest)
    ratio = digest_tokens / raw_tokens

    # next node receives ONLY the digest (isolated input schema)
    consumed = consumer_graph.invoke({"digest": digest})

    print("== EVAL 6: compactor / context hygiene ==")
    print(f"  raw tokens       : {raw_tokens}")
    print(f"  digest tokens    : {digest_tokens}")
    print(f"  ratio            : {ratio:.0%}")
    print(f"  consumer state keys: {sorted(consumed.keys())}  (raw NOT reachable)")
    print(f"  {consumed['ack']}")
    ok = ratio <= 0.45 and "digest" in consumed and "raw" not in consumed
    print(f"  RESULT: digest <= ~45% raw AND consumer sees only digest -> {ok}")
