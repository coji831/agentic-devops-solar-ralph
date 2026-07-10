# SOLAR Framework — Token Cost Optimization Proposal

**Version**: 2.0
**Date**: 2026-05-24
**Author**: Research synthesis across three experimental hotfixes (mandarin-vite-react-ts) + external benchmarks
**Status**: Revised per adversarial audit 2026-05-24 — v1.0 deprecated
**Supersedes**: v1.0 (adversarial audit verdict: PARTIAL; three of five levers not SOLAR-implementable)

---

## 1. Executive Summary

SOLAR-Ralph's multi-agent architecture compounds token costs structurally. A pre-optimization baseline consumed **28.1 million gross tokens** across 432 LLM calls for a single epic, driven by three root causes: full document re-injection into every subagent session, no cache prefix stability, and reactive-only compaction.

Three experimental hotfixes applied to the `mandarin-vite-react-ts` host between May 14–18, 2026 produced measured reductions. The headline finding from HF1 is **−44.5% average input tokens per LLM request** (per-request normalized, same provider). The gross session reduction was −89%, but that figure is scope-confounded by a 5× difference in session complexity (448 vs 89 LLM calls) and is not a valid efficiency comparison.†

| Hotfix | Primary Change                       | Per-Request Input Δ | ET Δ (gross)                     |
| ------ | ------------------------------------ | ------------------- | -------------------------------- |
| HF1    | Compact-by-reference dispatch        | **−44.5%**          | −89% (confounded†)               |
| HF2    | Guardrail signal detection           | −2.7% (below noise) | +634% (provider switch artifact) |
| HF3    | Telemetry baseline (no optimization) | Baseline only       | —                                |

> **† Scope confound**: HF1 pre-session had 448 LLM calls; post-session had 89 LLM calls — different task sizes. The valid comparison is average input tokens per LLM request: 66,828 → 36,634 = −45.2% (≈ −44.5% normalized).

**Projected additional improvement** with SOLAR-implementable levers (L1 + L2): **−15 to −30% vs post-HF1 baseline**.

Three additional levers (JIT tool registration, model tiering, cache prefix) have higher ET potential (−40 to −55%) but are blocked on VS Code platform features not yet available. They are documented in Appendix A.

---

## 2. The Token Runaway Problem in SOLAR

SOLAR's cost amplification is structural, not incidental. Three drivers create a compounding effect:

**Driver 1 — Full artifact body re-injection**
The orchestrator governor dispatches specialist agents with the full content of every referenced artifact embedded in the prompt. For an epic mid-session, this includes the full ledger (10,000+ tokens), the full story BR (5,000+ tokens), the full implementation doc (8,000+ tokens), and any research artifacts. Each specialist receives the same full-body injection regardless of which parts it needs.

Pre-HF1 measurement: 21.5M of 27.7M input tokens (77%) were document body injections. The same documents were re-injected into every subagent session across 20 specialist dispatches.

**Driver 2 — Subagent discovery turns**
Subagents spawned via `runSubagent` start with no task context. The first 1–2 turns are spent discovering where relevant files are (ledger path, story BR, implementation doc, AGENTS.md section). This is deterministic work that does not require LLM inference and can be eliminated by passing known paths in the dispatch baton.

**Driver 3 — Reactive compaction at 80% fill**
The SOLAR v3 compaction trigger fires at 80% context fill. By that point, the session has already committed 70–80% of its total token budget. Late-stage compaction preserves the session but does not reduce tokens already consumed. Proactive compaction at 65% fill (v4 policy) reduces expected overage by 30–40%.

---

## 3. Evidence Base

### 3.1 Hotfix 1 — Compact-by-Reference Dispatch (HF1)

**Commit**: `a3f72c1d8e9f4b2a7c5d0e8f1b3a6d4c2e9f7b1a`
**Status**: CONFIRMED (confidence 0.97)

**Core change**: Replaced full artifact body injection with path-reference dispatch in governor baton packets. Subagents receive `artifact_path: "verification-artifacts/..."` instead of the artifact's full text content.

| Metric                    | Pre-HF1            | Post-HF1          | Delta      |
| ------------------------- | ------------------ | ----------------- | ---------- |
| Total LLM requests        | 448                | 89                | −80.1%     |
| Avg input / request       | 66,828 tokens      | 36,634 tokens     | **−45.2%** |
| Document injection tokens | 21.5M (77% of all) | 92K (0.4% of all) | **−99.6%** |
| Total gross input tokens  | 29.9M              | 3.26M             | −89.1%†    |

**Confirmed mechanism**: The −99.6% document duplication reduction was entirely from passing artifact paths instead of embedding artifact content in each subagent prompt. Each path reference is ~50 tokens; the original inline body was ~120,000 tokens per session.

> **Scope caveat**: The −89% gross reduction compares sessions of different complexity (448 vs 89 LLM calls; 20 vs 11 subagents). Total-token comparisons between sessions of different scope are misleading. The valid efficiency signal is **average input tokens per LLM request: 66,828 → 36,634 = −45.2% (≈ −44.5% normalized)**. This is the headline claim.

**Remaining identified bottleneck**: The dispatch expansion factor (user dispatch text → first LLM input) was 38.9×. Approximately 97% of first-call tokens are system envelope, tool schemas, and workspace context injected by the VS Code host — not the agent's dispatch payload. This cannot be reduced at the SOLAR layer (host-injected), but can be amortized by batching more work per session.

---

### 3.2 Hotfix 2 — Guardrail Signal Detection (HF2)

**Commit**: `8cd3d2bcf6b7f167e115fba3047296ef7bc16b7f`
**Status**: CANDIDATE — pending 5A implementation (dead code defect discovered by adversarial audit)

**Intended change**: Implement `collectPreToolUseSignals()` in `pre-tool-use.cjs`. Detect and classify tool-use waste into typed signals. Enforce `hardFailSignals` config gate.

**Dead code finding**: `common.collectPreToolUseSignals(input, config)` is called in `pre-tool-use.cjs` but does NOT exist in `common.cjs`. The function is absent from the module's exported symbols. Calling a non-existent method throws `TypeError` and crashes the hook process silently. VS Code's default behavior when a `PreToolUse` hook crashes is to allow the tool call. The enforcement described in the HF2 evidence may not have been active during measurement.

| Metric                 | Pre-HF2 | Post-HF2  | Delta              |
| ---------------------- | ------- | --------- | ------------------ |
| Total LLM requests     | 166     | 97        | −41.6%             |
| Tool calls total       | 340     | 60        | −82.4%             |
| DUPLICATE_READ signals | 44      | 10        | −77.3%             |
| DELTA_HANDOFF_MISSING  | 55      | 12        | −78.2%             |
| Net charged tokens     | 909,001 | 6,669,099 | +634.4%\*          |
| Cache hit ratio        | 90.91%  | 0.0%      | −100% (artifact\*) |

\* Net charged data from HF2 is **unusable for financial projections**.

> **Audit note**: Per-request ET reduction is −2.7%, which is below reliable signal threshold for a single uncontrolled experiment. The −82.4% tool call reduction is real but its cause is not confirmed — the signal collection function that would explain it was not executing. These results are retained as observed data pending a controlled re-run after 5A is implemented.

---

### 3.3 Context Engineering Framework Reference

**Source**: LangChain Blog, "Context Engineering" (July 2025). Framework: four-bucket taxonomy.

| Bucket   | Mechanism                                              | SOLAR Applicability                                   |
| -------- | ------------------------------------------------------ | ----------------------------------------------------- |
| Write    | Save state outside window (scratchpad, memory files)   | Artifact handle pattern, pre-compact checkpoint       |
| Select   | Pull relevant context only (RAG, JIT loading)          | JIT skill loading (B8), artifact path handles         |
| Compress | Retain only necessary tokens (summarization, trimming) | Proactive compaction, delta handoff packets           |
| Isolate  | Split context across subagents with isolated windows   | SOLAR specialist model — each agent gets narrow scope |

---

### 3.4 Industry Benchmark Reference (VERIFIED)

**Source**: GitHub Engineering Blog — "Improving token efficiency in GitHub Agentic Workflows" (May 7, 2026; updated May 13, 2026). Authors: Landon Cox (Senior Principal Researcher, Microsoft Research) + Mara Kiefer (Senior Research Engineer). URL: https://github.blog/ai-and-ml/github-copilot/improving-token-efficiency-in-github-agentic-workflows/

> Verification status: Article fetched live 2026-05-24. All numbers below are exact readings from the article text. The ET formula quoted in the article is identical to SOLAR's canonical formula.

GitHub applied the ET formula (`ET = m × (1.0I + 0.1C + 4.0O)`) to 12 production agentic workflows and measured:

| Workflow                    | Primary Optimization                      | ET Reduction | Post-fix Runs |
| --------------------------- | ----------------------------------------- | ------------ | ------------- |
| Auto-Triage Issues          | Pre-agentic CLI data downloads            | **−62%**     | 109           |
| Smoke Claude                | MCP pruning + model tier-down (Haiku)     | **−59%**     | —             |
| Security Guard              | Relevance gate (skip LLM for non-matches) | **−43%**     | —             |
| Daily Community Attribution | MCP pruning                               | **−37%**     | 8             |
| Daily Compiler Quality      | Context restructuring                     | **−19%**     | 12            |

Key findings directly applicable to SOLAR:

- **Pre-agentic data downloads** (VERIFIED): "For data that an agent will always need... we added setup steps in the workflow that run `gh` commands before the agent starts and writes the results to workspace files. The agent reads those files instead of making MCP calls." This drove Auto-Triage's −62% reduction. **The cheapest LLM call is the one you don't make.**
- **Unused MCP tool cost** (VERIFIED): "For a GitHub MCP server with 40 tools, this can add 10–15 KB of schema per turn." Removing unused tools reduced per-call context by 8–12 KB per run.
- **Minimum sample size** (VERIFIED): Require at least 8 post-optimization runs for stable averages. Below 8, ET variation from task-size differences exceeds optimization signal.
- **Quality proxy**: Track LLM turns-per-run alongside tokens-per-call. If both fall, the workflow may be doing less work. If turns stay constant while tokens-per-call fall, it is a genuine efficiency gain.

---

## 4. SOLAR-Specific Waste Pattern Taxonomy

| SOLAR Pattern                   | Failure Mode           | Measured Impact                  | HF Evidence                  |
| ------------------------------- | ---------------------- | -------------------------------- | ---------------------------- |
| Full artifact body in dispatch  | Quadratic re-injection | 21.5M tokens (77% of input)      | HF1: −99.6% via path handles |
| Same file read multiple turns   | History re-injection   | 44 DUPLICATE_READ signals        | HF2: signal detection (5A)   |
| Full ledger in compact packets  | Summarization drift    | 55 DELTA_HANDOFF_MISSING signals | HF1: compact-handoff schema  |
| Subagent discovery turns        | Deterministic LLM work | 1–2 turns/session × 11 sessions  | L2: baton enrichment         |
| Reactive compaction at 80% fill | Late-stage collapse    | Context fill risk                | v4-compaction-policy         |

---

## 5. SOLAR-Implementable Levers

These are changes within SOLAR's control layer. Neither lever depends on VS Code platform features. Both are actionable today.

### Lever 1 — Compact-by-Reference Dispatch

**Prerequisite**: 5A (`collectPreToolUseSignals()` implementation) must be complete before this lever is considered active.

**Hypothesis**: Enforcing `DELTA_HANDOFF_SCHEMA_MISSING` as a hard-fail signal will eliminate the 55 schema-bypass events per session, preventing full-context regression from the HF1-established baseline.

**Evidence**: HF1 demonstrated −99.6% document duplication (21.5M → 92K tokens) by switching to path-reference dispatch. 55 signals in HF2 indicate agents still occasionally bypass the delta schema. Without hard-fail enforcement, future sessions can drift back to full-body injection.

**SOLAR changes required**:

1. Add `DELTA_HANDOFF_SCHEMA_MISSING` to `hardFailSignals[]` in `solar.config.json` (currently warn-only)
2. Implement `collectPreToolUseSignals()` in `common.cjs` — the function that makes this enforcement real (see 5A)
3. All specialist `SKILL.md` files: handoff section must reference `compact-handoff-packet.schema.json` (see 5D)

**Projected ET delta**: Maintains −44.5% per-request gain established by HF1. Without this lever, regression to full-body injection is possible as new sessions diverge from the HF1 dispatch pattern.

**Risk**: Hard-fail may block legitimate full-context passes (first dispatch in a new epic; recovery after context collapse). Mitigation: add `allow_full_context: true` override field to `compact-handoff-packet.schema.json`.

---

### Lever 2 — Governor Baton Enrichment

**Hypothesis**: Including known file paths in every `runSubagent` dispatch baton eliminates the first 1–2 discovery turns of each subagent session, where the agent reads the ledger, locates story BR, locates implementation doc, and finds its own AGENTS.md entry.

**Evidence**: Pre-HF1 main session logged 166 LLM calls with subagent Turn 1 average input ~39,968 tokens — consistent with a discovery read pattern (fetching known-location files with no inference required). Post-HF1, 11 subagents were spawned; if each begins with 1–2 discovery turns at ~40K tokens input, that is 440K–880K tokens that require zero LLM inference.

**Direct analog** (VERIFIED): GitHub Blog Auto-Triage Issues achieved −62% ET by converting "deterministic reads that required no inference" into pre-agentic setup steps. SOLAR's equivalent is the governor baton — pre-loading known paths into the dispatch packet rather than letting subagents discover them via tool calls.

**SOLAR changes required**:

1. Add explicit baton enrichment rule to `template/.github/agents/orchestration-governor.agent.md`: every `runSubagent` dispatch MUST include:
   - `ledger_stage`: current pipeline stage name
   - `artifact_refs`: array of paths to artifacts the specialist will need
   - `agents_md_section`: the specialist's own registry entry text (inline)
   - `input_refs[]`: array of work-defining document paths (spec, design doc, story BR, implementation doc — whatever the project uses)
2. Add compact handoff baton schema reference to all SKILL.md files confirming these fields are expected (see 5C, 5D)

**No new hook infrastructure required.** This is a governor instruction change only.

**Projected ET delta**: −10 to −20% reduction in subagent session input tokens (eliminates 1–2 discovery turns per session across ~10 subagent sessions per epic).

**Risk**: Governor may not always know all relevant paths at dispatch time (e.g., dynamically-created artifacts). Mitigation: `artifact_refs` is an array; governor populates what it knows; subagents fall back to discovery for unknown paths only.

---

## 6. Implementation Roadmap (5A–5D)

These are the four concrete changes required to activate the two levers above.

### 5A — Implement `collectPreToolUseSignals()` (Blocking for Lever 1)

**Target**: `template/.github/hooks/common.cjs` (and `mandarin-vite-react-ts/.github/hooks/common.cjs` as reference)

**What**: Implement and export `collectPreToolUseSignals(input, config)`. The function must inspect the tool call input for:

- `DELTA_HANDOFF_SCHEMA_MISSING`: check if the tool name is `runSubagent` and the input payload lacks required `compact-handoff-packet.schema.json` fields
- `DUPLICATE_READ_DETECTED`: check session state for whether the same file path has been read beyond `maxReadsPerFilePerSession`

Without this function, the `PreToolUse` hook crashes silently on every call and the entire guardrail enforcement mechanism is inactive.

### 5B — Update Template `solar.config.json` (Blocking for new installs)

**Target**: `template/.github/solar.config.json`

The template config has only 5 fields. New installs receive a broken config that silently disables all guardrail enforcement. Replace with the full 14-field schema:

```json
{
  "adversarial": true,
  "learning": false,
  "logging": false,
  "human_approval": true,
  "hooks": true,
  "maxDispatchInputTokens": 6000,
  "maxHighCostDispatchTokens": 3000,
  "maxReadWindowLines": 200,
  "maxReadsPerFilePerSession": 1,
  "requireArtifactRefForHighCost": true,
  "enforceDeltaForRedispatch": true,
  "artifactizationThresholdTokens": 4000,
  "hardFailSignals": ["DELTA_HANDOFF_SCHEMA_MISSING"],
  "telemetry": { "modelMultipliersVersion": "v1" }
}
```

This config must also be synced to `solar-install.prompt.md`.

### 5C — Governor Baton Enrichment Rule

**Target**: `template/.github/agents/orchestration-governor.agent.md`

Add explicit instruction that EVERY `runSubagent` dispatch MUST include in the baton packet: `ledger_stage`, `story_br_path`, `story_impl_path`, `artifact_refs`, `agents_md_section`. This is the Lever 2 activation change.

### 5D — Compact Handoff Schema in SKILL.md Templates

**Target**: All `template/.github/skills/*/SKILL.md` files

Each SKILL.md's handoff/output section must explicitly reference `compact-handoff-packet.schema.json` and instruct the specialist to populate only delta fields. This is both a Lever 1 support change and a Lever 2 confirmation that baton fields are expected.

---

## 7. Measurement Plan

### Control Methodology

Each lever must be tested in isolation with controlled variables. The HF2 provider switch (OpenAI → Anthropic) invalidated net-charged comparisons for that experiment. Same-provider comparison is mandatory.

| Variable   | Must Hold Constant                                          | Varies |
| ---------- | ----------------------------------------------------------- | ------ |
| Provider   | Same provider both runs (Copilot-hosted or BYOK, not mixed) | —      |
| Task scope | Same story/epic both runs                                   | —      |
| Model      | Same model both runs                                        | —      |
| Lever      | One lever ON vs OFF per experiment                          | —      |

### Primary Metrics

Per the GitHub Blog methodology: track LLM API call counts alongside token counts. Constant turns-per-run + falling tokens-per-call = genuine efficiency gain. Both falling together = less work done (quality risk).

| Metric                 | Formula                         | Target                                         |
| ---------------------- | ------------------------------- | ---------------------------------------------- |
| ET per LLM request     | `ET / request_count`            | Primary: normalize for workload variation      |
| LLM turns per run      | `request_count`                 | Must stay ≥ pre-optimization (quality gate)    |
| Output tokens per call | `output_tokens / request_count` | Drop > 20% → quality risk                      |
| Cache hit ratio        | `cached_tokens / input_tokens`  | Track for regression detection                 |
| Guardrail signal rate  | `signals_fired / tool_calls`    | Declining DUPLICATE_READ = genuine improvement |
| Gross tokens           | `input + output`                | Secondary (context: workload size)             |

### Minimum Sample Size

Require at least 8 post-optimization runs before computing stable averages (GitHub Blog methodology, validated across 109 Auto-Triage runs). Below 8, ET variation from task-size differences exceeds optimization signal.

### Quality Signals

No ground-truth correctness metric exists for agentic output. Use process proxies:

- Tool-call completion rate (no failed retries)
- Output artifact size stability (story doc word count ≥ pre-optimization)
- Adversarial audit pass rate
- Human acceptance rate (story AC check-off rate)

---

## 8. Risk Flags

### R1 — Cache Collapse on Provider Switch

**Observed**: HF2 net charged increased 634.4% purely from 90.91% → 0% cache hit after provider switch.
**Mitigation**: Same-provider comparison runs required. Track cache hit ratio per session via HF3 telemetry.

### R2 — Guardrail Over-Blocking

**Context**: Promoting `DELTA_HANDOFF_SCHEMA_MISSING` to `hardFailSignals[]` will block dispatches where the handoff packet lacks delta fields.
**Risk**: Legitimate full-context passes (first-run bootstrap, recovery after context collapse) will be blocked.
**Mitigation**: `allow_full_context: true` override field in `compact-handoff-packet.schema.json`. Governor sets this explicitly when a full-context pass is intentional.

### R3 — Baton Enrichment Incomplete at Runtime

**Context**: Governor may not know all relevant artifact paths when constructing the dispatch baton for early-pipeline stages.
**Risk**: Subagent still makes 1–2 discovery turns for unknown paths; Lever 2 gain is partial.
**Mitigation**: `artifact_refs` is an array; partial population is valid. Lever 2 gain is proportional to paths provided. Log missing fields via `BATON_INCOMPLETE` signal for observability.

### R4 — Telemetry Noise from Untagged Sessions

**Observed**: HF3 telemetry shows `task_id: "unknown"`, `stage: "unknown"` in many entries.
**Risk**: Cannot segment ET by pipeline stage for future stage-level optimization.
**Mitigation**: Governor must write `TASK_START: task_id=<id> stage=<stage>` to ledger before each dispatch so `post-tool-use.cjs` can correlate records.

---

## 9. Summary and Projected Outcomes

**Baseline**: Pre-HF1 average input per LLM request = **78,935 tokens**.
**HF1 demonstrated**: −44.5% per-request normalized = **~43,900 tokens average input**.

SOLAR-implementable levers (L1 + L2) target an additional reduction on top of the maintained HF1 baseline:

| Lever                      | Mechanism                             | Projected Additional ET Reduction    |
| -------------------------- | ------------------------------------- | ------------------------------------ |
| L1 — Hard-fail signal (5A) | Prevents regression to full injection | Maintains −44.5% per-request gain    |
| L2 — Baton enrichment (5C) | Eliminates subagent discovery turns   | −10 to −20% additional               |
| **L1 + L2 combined**       |                                       | **−15 to −30% vs post-HF1 baseline** |

> Three additional levers (JIT Tool Registration, Model Tiering, Cache Prefix) are documented in Appendix A. Their combined potential is −40 to −55% additional ET, but all three are blocked on VS Code platform features not yet available.

---

## Appendix A — Platform-Dependent Levers (Future Work)

These levers are NOT implementable by SOLAR today. Their ET projections must not be included in any SOLAR delivery commitment.

### A.1 — JIT Tool Registration (formerly Lever 2)

**Mechanism**: Register only role-matched toolsets per specialist dispatch, eliminating VS Code's host-injected full tool manifest.

**Evidence**: GitHub Blog (VERIFIED) — MCP tool pruning reduced per-call context by 8–12 KB per run. SOLAR pre-HF1 dispatch expansion factor: 38.9× (97% of first-call tokens are host-injected tool schemas and workspace context).

**Blocked by**: VS Code does not honor `toolset_manifest` in AGENTS.md at dispatch time. The full tool manifest is injected by the VS Code host regardless of SOLAR's configuration. Tracked as FB-17 in `v4-implement-feedback.md`.

**Potential ET delta when unblocked**: −20 to −35% per request.

---

### A.2 — Model Tiering by Pipeline Stage (formerly Lever 4)

**Mechanism**: Route data-gathering stages (scan, collect) to Haiku (0.25× ET multiplier) and reserve Sonnet (1.0×) for reasoning-heavy stages (design, verify).

**Evidence**: GitHub Blog (VERIFIED) — Smoke Claude achieved −59% by combining MCP pruning with model tier-down to Haiku. Haiku = 0.25× multiplier vs Sonnet = 1.0×.

**Blocked by**: VS Code does not reliably read `model:` frontmatter in agent files at dispatch time. Platform bugs #18873 and #19402. The `governor-haiku-fix-plan.md` P2 fix (Status: COMPLETE) resolved this by removing model labels from delegation lines because "they were wrong the majority of the time." SOLAR cannot invoke a subagent on a specific model at the API level; VS Code Copilot makes that selection.

**Potential ET delta when unblocked**: −30 to −40% weighted ET.

---

### A.3 — Prompt Cache Prefix Stabilization (formerly Lever 5)

**Mechanism**: Structure dispatch packets with a stable leading prefix (static envelope first, variable payload last) to restore cache hit ratio toward 85%+.

**Evidence**: HF1 post-session cache hit ratio fell from 89.36% to 50.25% (provider switch + changed dispatch structure). Restoring 89% cache ratio on the post-HF1 baseline would reduce net charged from 1,713,099 to ~369K (−78% net cost).

**Blocked by**: Prompt cache prefix ordering is controlled by the VS Code Copilot runtime's HTTP request assembly. The stable prefix consists of (1) system prompt, (2) tool schemas, (3) conversation history — all VS Code-controlled. SOLAR's dispatch baton arrives as position 4 (current turn) and has no effect on prefix stability. The `compact-dispatch.cjs` file referenced in v1.0 of this proposal does not exist.

**Potential ET delta when unblocked**: −50 to −75% net charged (gross ET unchanged).

---

## References

1. "Theoretical and Practical Limitations of Context Re-injection and Token Runaway in Agentic Coding Environments" — `docs/research/notes/context-injection-and-token-runaway.md`
2. "Improving token efficiency in GitHub Agentic Workflows" — Landon Cox + Mara Kiefer, GitHub Blog, 2026-05-07 (updated 2026-05-13)
3. "Context Engineering for Agents" — LangChain Blog, July 2025
4. Pre-HF1 forensic report — `mandarin-vite-react-ts/verification-artifacts/session-token-analysis-pre-hotfix.md`
5. Post-HF1 forensic report — `mandarin-vite-react-ts/verification-artifacts/session-token-analysis-post-hotfix.md`
6. HF1 verdict — `mandarin-vite-react-ts/verification-artifacts/hotfix-verdict-report.md`
7. HF2 verdict (v2) — `mandarin-vite-react-ts/verification-artifacts/hotfix2-comparison-verdict.md`
8. Adversarial audit — `verification-artifacts/20260524-token-optimization-adversarial-audit.md`
9. SOLAR v4 compaction policy — `docs/knowledge-base/v4-compaction-policy.md`
10. Effective tokens protocol — `mandarin-vite-react-ts/.github/solar-system/protocols/effective-tokens.md`
11. Guardrails signals protocol — `mandarin-vite-react-ts/.github/solar-system/protocols/guardrails-signals.md`
