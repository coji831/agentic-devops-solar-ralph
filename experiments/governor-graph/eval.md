# governor-graph — eval results (B2)

Criteria + recorded results for the 6 evals. Each eval records pass/fail + what was learned.

---

## EVAL 3 — deterministic routing (step 3.2)

**Criteria:** `classify` node + conditional edge routes each sample to exactly one handler; same input → same route every run (5× per sample).

**Result:** ✅ PASS — 4 samples × 5 runs = 20/20 stable routes.

| sample                        | intent          | deterministic |
| ----------------------------- | --------------- | ------------- |
| `"remember this decision"`    | capture         | True          |
| `"how do we do RAG"`          | query (default) | True          |
| `"draft an outreach message"` | propose         | True          |
| `"post to LinkedIn"`          | publish         | True          |

**Learned:** conditional edges = pure-function router (no LLM re-read, no orchestrator round-trip); the `path_map` is the single place routing is defined; deterministic routing is the v5 answer to TD-4-1 (direct-invocation bypass) and prompt-guessed dispatch.

---

## EVAL 1 — HITL interrupt / adversarial gate (step 3.3)

**Criteria:** an adversarial-review node `interrupt()`s; resume with `approve` → continue to `complete`; resume with `deny` → `rework` branch (Ralph loop) → re-pause → approve → complete.

**Result:** ✅ PASS — all 3 branch checks true (checkpointer = MemorySaver for this eval; SQLite in 3.4).

| action                | result                                                                                        |
| --------------------- | --------------------------------------------------------------------------------------------- |
| run → pause           | `__interrupt__` present; payload `{'ask': 'Adversarial review: approve or deny the output?'}` |
| resume `approve`      | stage=`complete`, no pause, rework=0                                                          |
| resume `deny`         | stage=`implemented` (re-paused at next adversarial review), rework=1                          |
| then resume `approve` | stage=`complete`, no pause, rework=1                                                          |

**Learned:** `interrupt()` is the native human-in-the-loop primitive — a hard pause with an inspectable payload; resume via `Command(resume=...)`; the interrupted node re-runs and `interrupt()` returns the resume value on the second pass. This is the v5 replacement for `vscode_askQuestions` + the design/adversarial approval flow — and it is channel-agnostic (any client can answer).

---

## EVAL 2 — checkpointer / durable execution (step 3.4)

**Criteria:** attach SQLite checkpointer; run to a mid-point; recreate graph/process; resume from checkpoint exactly where it stopped.

**Result:** ✅ PASS — two separate processes over the same `checkpoints.sqlite` file.

| phase                               | output                                                                                                       |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `write` (process 1)                 | paused at step2 `{'ask': 'continue past step 2?'}`; state step=1, log=`['step1 done']`; exits WITHOUT resume |
| — process boundary (session lost) — |                                                                                                              |
| `resume` (process 2)                | fresh graph, same file → final step=3, log=`['step1 done','step2 continued (yes)','step3 done']` — PASS      |

**Learned:** `SqliteSaver.from_conn_string(path)` is a **context manager** (must wrap compile+invoke in `with`); each checkpoint commits to the file, so a brand-new graph instance (even a new process) can resume a thread by `thread_id`. This is the v5 replacement for `.ai_ledger.md` cold-read restart-safety — durable execution proven across process boundaries. Note: dep `langgraph-checkpoint-sqlite` 3.1.1 was installed — the gap flagged in feasibility §13.9.2.

---

## EVAL 4 — streaming (step 3.5)

**Criteria:** stream the graph run; node outputs arrive incrementally (`astream` / `stream_mode="updates"`), SSE-style framing (simulates the R9 channel gateway).

**Result:** ✅ PASS — 4 node events streamed incrementally in order.

| event       | data                                       |
| ----------- | ------------------------------------------ |
| `gate`      | `{'log': ['gate: materials READY']}`       |
| `plan`      | `{'log': ['plan: design approved']}`       |
| `implement` | `{'log': ['implement: artifact written']}` |
| `review`    | `{'log': ['review: APPROVED']}`            |

**Learned:** `astream(..., stream_mode="updates")` yields a chunk per completed node; `stream_mode="values"` yields the full state per step. SSE framing (`event:`/`data:`) maps directly to the R9 channel gateway — Slack/WhatsApp/HTTP-SSE are front-ends to the same graph (convergence §13.5).

---

## EVAL 6 — compactor node (step 3.6)

**Criteria:** a compactor collapses raw specialist output into a compact digest; the next node receives ONLY the digest (channel isolation); token delta measured.

**Result:** ✅ PASS — 120 raw tokens → 44 digest tokens (37% ratio ≤ 45%); the consumer's input schema had only `digest` (raw unreachable).

| metric              | value                                   |
| ------------------- | --------------------------------------- |
| raw tokens          | 120                                     |
| digest tokens       | 44                                      |
| ratio               | 37%                                     |
| consumer state keys | `['ack', 'digest']` — raw NOT reachable |

**Learned:** channel isolation = the consumer graph's input schema defines exactly what it can see; the compactor (a deterministic heuristic here; an LLM node in production) collapses raw + decisions into the ONLY input of the next specialist. This is the token-cost + memory-surface mechanism of v5: no context bloat accumulates in any orchestrator window, because each specialist's context is bounded to its digest.

---

## EVAL 5 — hub KB MCP call from a node (step 3.7)

**Criteria:** a `retrieve` node launches the hub KB MCP server over stdio, calls `kb_search`, returns the top hit into state; when the hub is absent (`--no-hub`, foreign-repo path) the node skips gracefully (no crash) — §13.14 graceful degradation.

**Result:** ✅ PASS (both paths).

| path        | output                                                                       |
| ----------- | ---------------------------------------------------------------------------- |
| hub present | status=`ok`; node returned 3 real `[jobs]` rows for "RAG streaming"          |
| `--no-hub`  | status=`skipped (hub absent - foreign repo path)`; graph completed, no crash |

**Learned:** the node→MCP-tool pattern works (v5 shape-a adapter): a node can host an MCP stdio client and call hub tools as ordinary function calls. Graceful degradation = the hub is an optional uplink (§13.14): absent hub → node skips, never fails. This validates hub↔SOLAR convergence (§13.5) — one graph can call the hub KB, and any repo (owned or not) runs the same harness.
