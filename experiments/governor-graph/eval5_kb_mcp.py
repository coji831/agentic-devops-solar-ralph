"""EVAL 5 (step 3.7): call hub KB MCP from a node — hub ↔ SOLAR convergence.

A `retrieve` node launches the hub's KB MCP server (`Resume/mcp/kb_server.py`)
over stdio, calls `kb_search`, and returns the top hit into state. This proves
the node→MCP-tool pattern (v5 shape-a adapter). Per §13.14 data sovereignty:
when the hub is absent (`--no-hub` = foreign repo path), the node SKIPS
gracefully instead of crashing.

Usage:
    python eval5_kb_mcp.py --query "RAG streaming"     # hub present
    python eval5_kb_mcp.py --query "RAG streaming" --no-hub   # graceful skip
"""
import argparse
import asyncio
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

# Owned-repo uplink: the hub is mounted in this workspace (§13.14).
HUB_ROOT = Path(r"C:\CodeProjects\Personal\Resume")
PY = r"C:/Users/Hiep/AppData/Local/Programs/Python/Python312/python.exe"
SERVER = "mcp/kb_server.py"


class State(TypedDict):
    query: str
    hub_available: bool
    kb_hits: str
    kb_status: str


async def _kb_search(query: str, limit: int = 3) -> str:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command=PY, args=[SERVER], cwd=str(HUB_ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            res = await session.call_tool("kb_search", {"query": query, "limit": limit})
            return "\n".join(c.text for c in res.content if getattr(c, "text", None))


def retrieve(state: State) -> dict:
    if not state.get("hub_available"):
        # foreign-repo path: no hub, no kb:// resources -> skip, never crash
        return {"kb_status": "skipped (hub absent - foreign repo path)", "kb_hits": ""}
    try:
        hits = asyncio.run(_kb_search(state["query"]))
        return {"kb_hits": hits, "kb_status": "ok"}
    except Exception as e:  # graceful degradation: never crash the graph
        return {"kb_status": f"unavailable: {type(e).__name__}", "kb_hits": ""}


g = StateGraph(State)
g.add_node("retrieve", retrieve)
g.add_edge(START, "retrieve")
g.add_edge("retrieve", END)
graph = g.compile()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", default="RAG streaming")
    ap.add_argument("--no-hub", action="store_true", help="simulate a foreign repo with no hub")
    args = ap.parse_args()

    out = graph.invoke({"query": args.query, "hub_available": not args.no_hub})
    print("== EVAL 5: hub KB MCP call from a node ==")
    print("  status:", out.get("kb_status"))
    print("  hits:")
    print(out.get("kb_hits") or "  (none)")
    ok = out.get("kb_status") == "ok" and bool(out.get("kb_hits"))
    print(f"  RESULT: node returned real KB data -> {ok}")
