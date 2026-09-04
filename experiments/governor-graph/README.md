# governor-graph — SOLAR v5 prototype (B2)

Proves the LangGraph primitives behind SOLAR-Ralph v5 (governor-as-graph, see
`../docs/versions/v5.md`). One concept per eval. The full v5 governor will be
built on this once the decision gate (step 3.9) passes.

## What each eval proves

| Eval      | File                 | Proves                                                                           |
| --------- | -------------------- | -------------------------------------------------------------------------------- |
| 3.1 state | `prototype.py`       | StateGraph + TypedDict state; reducers accumulate across nodes                   |
| EVAL 3    | `prototype.py`       | conditional edges = deterministic routing (capture/query/propose/publish)        |
| EVAL 1    | `prototype.py`       | HITL adversarial gate: approve → complete, deny → rework loop (Ralph)            |
| EVAL 2    | `eval2_durable.py`   | SQLite durable execution: resume after session loss in a NEW process             |
| EVAL 4    | `eval4_stream.py`    | node outputs stream incrementally (SSE-style → R9 channel gateway)               |
| EVAL 6    | `eval6_compactor.py` | channel isolation + token-cost (raw → digest; next node sees only digest)        |
| EVAL 5    | `eval5_kb_mcp.py`    | node → hub KB MCP tool call (convergence) + graceful degradation when hub absent |

## Setup

- Python 3.12. Deps: `pip install -r requirements.txt` (`langgraph`, `mcp`, `langgraph-checkpoint-sqlite`).
- Hub KB (EVAL 5 only): the hub repo (`Resume/`) must be reachable at the path in
  `eval5_kb_mcp.py` with `data/kb.db` built. Without it, run with `--no-hub` to see graceful degradation.

## Run

```bash
python prototype.py                            # 3.1 state + EVAL 3 routing + EVAL 1 interrupt
python eval2_durable.py write                  # phase 1: run to mid-point, "lose session"
python eval2_durable.py resume                 # phase 2: NEW process resumes from checkpoint
python eval4_stream.py                         # EVAL 4 streaming
python eval6_compactor.py                      # EVAL 6 compactor + token delta
python eval5_kb_mcp.py --query "RAG streaming"           # hub present
python eval5_kb_mcp.py --query "RAG streaming" --no-hub  # graceful degradation
```

## Results

All 6 evals **PASS** — criteria + recorded results in `eval.md`.

## Design notes

- **Sovereignty (§13.14):** repo-bounded by default; the hub is an optional uplink —
  absent hub → EVAL 5 node skips, never crashes.
- **Convergence (§13.5):** the same graph runs from VS Code, CLI, or a future channel
  gateway (R9). IDE-agnostic path in the v5 plan (§13.11).
- **Decision gate (step 3.9):** this prototype's results feed the adopt-v5 recommendation.
