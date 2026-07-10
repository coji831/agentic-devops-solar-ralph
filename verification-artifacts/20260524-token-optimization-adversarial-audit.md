# Adversarial Audit: SOLAR Token Cost Optimization Proposal

**Audit target**: `docs/work-logs/solar-token-optimization-proposal.md`  
**Auditor**: Review Auditor (non-author specialist)  
**Date**: 2026-05-24  
**Verdict**: PARTIAL — significant evidence weaknesses and implementability gaps; two levers are actionable; three are not currently implementable by SOLAR

---

## 1. Verdict Summary

| Item                                          | Verdict     | Reason                                                                                                                                                                                                                                                                                        |
| --------------------------------------------- | ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Lever 1 — Compact-by-Reference Dispatch       | **PARTIAL** | Hard-fail enforcement is partially implemented but the signal collection function is a broken stub. The mechanism works at the hook level but depends on completing `collectPreToolUseSignals()`.                                                                                             |
| Lever 2 — JIT Tool Registration               | **FAIL**    | Self-admitted in the proposal: VS Code injects the full tool manifest regardless of SOLAR's `toolset_manifest` field. Not implementable within SOLAR's control layer today.                                                                                                                   |
| Lever 3 — Pre-Agentic Data Download Bootstrap | **FAIL**    | `session-start.cjs` does not exist anywhere in the repository. The mechanism conflates the main-session `SessionStart` hook with subagent context — these are not the same lifecycle point.                                                                                                   |
| Lever 4 — Model Tiering                       | **FAIL**    | `governor-haiku-fix-plan.md` P2 explicitly documents that VS Code does not reliably read subagent frontmatter `model:` at dispatch time (platform bugs #18873, #19402). This was fixed by REMOVING model labels, not adding them. Lever 4 proposes rebuilding the thing the fix plan removed. |
| Lever 5 — Prompt Cache Prefix Stabilization   | **FAIL**    | `compact-dispatch.cjs` does not exist. Prompt cache prefix ordering is controlled by the VS Code host's HTTP request assembly — SOLAR has no pathway to inject `cache_control` headers or reorder turns.                                                                                      |
| HF1 Evidence                                  | **PARTIAL** | −89% absolute is scope-confounded (5× session size reduction). Normalized per-request shows −44.5% — still meaningful but not −89%. The verdict report itself flags this.                                                                                                                     |
| HF2 Evidence                                  | **PARTIAL** | −82.4% tool call reduction is real but partially unexplained. Per-request ET is −2.7% — near noise floor. The `collectPreToolUseSignals()` function that HF2 claims to implement does not exist in `common.cjs`.                                                                              |
| Stacked −55 to −70% ET projection             | **FAIL**    | Arithmetically derived from three non-implementable levers (L2, L4, L5) plus one partially broken lever (L1) plus one mechanistically unsupported lever (L3).                                                                                                                                 |
| "−80%+ with prompt-cache restoration"         | **FAIL**    | Prompt caching is a VS Code host feature. Attributing it to SOLAR is a scope violation.                                                                                                                                                                                                       |
| Overall proposal                              | **PARTIAL** | One lever (L1 hardening) is clearly actionable with a concrete code fix. One lever (L3 baton enrichment, reframed correctly) is partially actionable. The three non-implementable levers should be removed or reclassified as "requires VS Code platform changes."                            |

---

## 2. Evidence Legitimacy Assessment

### 2.1 Quantitative Claims

| Claim                                                  | Status                      | Chain of Custody                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------------------------------------------------ | --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| −89% gross token reduction (HF1)                       | **UNVERIFIED as presented** | Measured from raw JSONL (source: `hotfix-verdict-report.md`, confidence 94/95%). However the comparison is scope-confounded: 448 pre vs 89 post LLM requests. The verdict report explicitly states "total token comparisons alone would be misleading" and provides the −44.5% per-request normalized figure as the fair metric. The proposal surfaces the absolute −89% in the executive summary without the normalization caveat. |
| −99.6% document duplication reduction                  | **VERIFIED**                | Directly attributable to path-reference dispatch replacing full-body injection. Mechanism is confirmed (21.5M → 92K tokens). This is the strongest single data point in the proposal.                                                                                                                                                                                                                                               |
| −82.4% tool call reduction (HF2)                       | **ESTIMATED**               | Measured from raw JSONL. However, per-request ET gain is only −2.7%, which is below reliable signal threshold for a single uncontrolled experiment. The session scope also changed (340→60 calls, 232→168 LLM requests). No same-task controlled comparison was run.                                                                                                                                                                |
| −29.5% ET reduction (HF2)                              | **ESTIMATED**               | Gross tokens fell by 23.8%; ET fell by 29.5%. The differential between these two figures is not explained. With 0% cache hit and the ET formula (1.0×I + 0.1×C + 4.0×O), ET≈Gross when C≈0. The 5.7% delta is likely model-mix noise.                                                                                                                                                                                               |
| +634.4% net charged increase (HF2)                     | **VERIFIED**                | Directly measured. The proposal's dismissal of this as an "instrumentation artifact" is the most aggressive claim in the document. While the provider switch explanation is credible, it means HF2's net cost data is entirely unusable as a baseline for any financial projection.                                                                                                                                                 |
| 38.9× dispatch expansion factor                        | **ESTIMATED**               | Calculated from forensic reports as `first_input_tokens / user_dispatch_tokens`. This ratio is real, but the interpretation — that this is addressable by SOLAR — is incorrect (see Lever 2 below).                                                                                                                                                                                                                                 |
| −55 to −70% stacked ET projection                      | **ESTIMATED/UNVERIFIED**    | Derived by summing lever projections, several of which are for non-implementable changes. Even accepting all lever estimates at face value, the independence assumption is questionable (L1 and L3 address overlapping waste categories).                                                                                                                                                                                           |
| "−78% net cost available by restoring cache" (Lever 5) | **ESTIMATED**               | Back-calculated from HF1 cache ratios under a hypothetical. Not measured. Depends on VS Code host behavior SOLAR cannot control.                                                                                                                                                                                                                                                                                                    |

### 2.2 Web Citations

**GitHub Blog, May 2026 (Cox + Kiefer)**: Numbers cited are internally consistent with documented GitHub Actions agentic workflow patterns. The mechanism (pre-agentic CLI steps eliminating LLM calls) is independently plausible. However:

- The specific −62% Auto-Triage figure, −59% Smoke Claude figure, and −43% Security Guard figure cannot be verified from within this audit.
- The "10–15 KB per tool schema" MCP overhead claim is plausible but the 2,500–3,000 tokens/schema figure in the proposal body is inconsistent with that range (10–15 KB / 4 chars/token ≈ 2,500–3,750 tokens/schema — marginally consistent but the lower range doesn't match).
- Attribution to "Landon Cox (Microsoft Research) + Mara Kiefer (Senior Research Engineer)" is specific enough that fabrication risk is low, but unverified.
- **Flag**: REFERENCE-LEVEL. One external source. Not validated against SOLAR's specific VS Code Copilot tool injection behavior.

**LangChain Blog, July 2025**: The four-bucket taxonomy (Write / Select / Compress / Isolate) is a real published framework. The SOLAR mapping in the proposal is qualitatively reasonable. No numerical claims drawn from this source.

---

## 3. Practicality Scorecard

### Lever 1 — Compact-by-Reference Dispatch

**Implementable in SOLAR: PARTIAL**

The `PreToolUse` hook mechanism in VS Code Copilot CAN deny tool use — `permissionDecision: "deny"` is a valid hook response. The `pre-tool-use.cjs` is already wired to read `hardFailSignals` from `solar.config.json` and emit a deny response. This architecture is sound.

**Critical defect**: `common.collectPreToolUseSignals(input, config)` is called in `pre-tool-use.cjs` but does NOT exist in `common.cjs`. The module exports are: `buildCompactProjection, estimateTokens, getSessionKey, loadConfig, normalizePath, readLedger, readHookState, isSolarActive, writeHookState` — no signal collection function. Calling a non-existent method throws `TypeError` and crashes the hook process. VS Code's behavior when a `PreToolUse` hook crashes is to allow by default (safer than blocking). The entire HF2 claim that `hardFailSignals` was enforced may be invalid — the enforcement code is broken.

**Template gap**: `template/.github/solar.config.json` has only 5 fields and no `hardFailSignals` array. The installed scaffold cannot enforce this lever until the template is updated.

**Governor bypass risk**: Even if the hook works, the governor IS the caller of `runSubagent`. If the governor itself is the agent whose output is being checked, and the governor constructs a dispatch packet that triggers the signal, the governor would need to modify its own behavior. Hard-fail signals add friction; they do not prevent the governor from reformulating the dispatch to avoid triggering detection.

### Lever 2 — JIT Tool Registration

**Implementable in SOLAR: NO**

The proposal states this explicitly: "Tool restriction at the SOLAR layer is advisory — VS Code hosts currently inject the full manifest regardless. This lever's full value activates once VS Code agent mode supports per-agent toolset scoping (tracked in FB-17)."

Adding `toolset_manifest` to AGENTS.md is a documentation exercise, not an optimization. The −20 to −35% projection is conditioned on a VS Code platform feature that does not exist. Presenting this projection in the executive summary without the conditional is misleading.

The only sub-lever that is partially implementable: adding a `TOOLSET_LOADED` signal with token load estimate (observability only — no actual reduction). Milestone 1 should not include this lever's ET delta in its projections.

### Lever 3 — Pre-Agentic Data Download Bootstrap

**Implementable in SOLAR: NO (as described); PARTIAL (reframed)**

Two structural problems:

**Problem A — The hook doesn't exist**: `session-start.cjs` is nowhere in the repository. The `SessionStart` hook would need to be added to `hooks.json`, the script created, and the mechanism designed from scratch.

**Problem B — Wrong lifecycle point**: The `SessionStart` hook fires once when the MAIN conversation session starts — before the governor runs. Subagents are spawned later via `runSubagent` tool calls inside the governor's session. They run in isolated subagent contexts. A file written by `session-start.cjs` at conversation start:

- Can be written to disk (e.g., `verification-artifacts/session-bootstrap-{task_id}.json`)
- But a subagent spawned hours later via `runSubagent` has NO automatic mechanism to find or load this file — it must be explicitly told the path in the dispatch baton
- The governor must already know the file's path when constructing the baton

If the governor already knows the relevant paths to include in the baton, it doesn't need a bootstrap file — it can include those paths directly. The bootstrap file is an indirection with no throughput advantage over governor baton enrichment.

**The actual actionable version**: Governor baton enrichment — include known file paths (ledger, story BR, implementation doc, AGENTS.md section) in the dispatch packet as direct references. This eliminates subagent Turn 1 discovery reads. This is implementable TODAY via governor instruction changes and requires no new hook infrastructure. It is a change to `template/.github/agents/orchestration-governor.agent.md` and the handoff baton schema.

### Lever 4 — Model Tiering

**Implementable in SOLAR: NO (reliably)**

The kill-shot: `governor-haiku-fix-plan.md` P2, Status COMPLETE, explicitly documents that the `model:` frontmatter field in agent files is NOT reliably read by VS Code's Task tool at dispatch time, referencing platform bugs #18873 and #19402. The applied fix was to REMOVE model labels from delegation lines because they "were wrong the majority of the time."

Lever 4 proposes adding `modelTierMap` to `solar.config.json` and passing `model_tier_hint` in the governor baton. But:

- `solar.config.json` values are read by SOLAR hooks (Node.js scripts), not by VS Code's model selection system
- Passing `model_tier_hint` as text in the dispatch baton relies on VS Code reading and honoring that text — the same pathway that was already documented as broken
- SOLAR cannot invoke a subagent on a specific model at the API level; VS Code Copilot makes that selection

The HF2 evidence for this lever (Haiku being used for Data Collector) is real, but it appears the model was manually configured in that experiment, not automatically enforced by SOLAR's framework. There is no evidence that SOLAR's code forced the model selection.

Model tiering may be achievable in the future if VS Code adds deterministic model routing for `runSubagent`, but it cannot be reliably implemented by SOLAR today.

### Lever 5 — Prompt Cache Prefix Stabilization

**Implementable in SOLAR: NO**

`compact-dispatch.cjs` does not exist in the repository. But even if it were created, the fundamental premise is incorrect:

The prompt cache hit ratio is determined by how the VS Code Copilot runtime assembles the HTTP request body sent to the LLM provider API. The stable prefix for cache hits consists of:

1. System prompt (injected by VS Code from instruction files)
2. Tool schemas (injected by VS Code from the registered tools)
3. Conversation history (managed by VS Code)
4. The current turn content

SOLAR's baton content arrives as part of the current turn (4). Any prefix ordering SOLAR enforces within the baton is irrelevant to cache prefix stability — VS Code controls (1), (2), and (3), and these dominate the prefix. Even if SOLAR perfectly ordered its baton fields, a VS Code version update that changes system prompt wording or tool schema ordering would invalidate the cache.

The HF1 cache drop from 89% to 50% was caused by provider switch + changed dispatch structure — SOLAR-controlled changes. The HF2 cache drop to 0% was caused by provider switch. These do not show that SOLAR can restore cache; they show that SOLAR's own changes can DAMAGE cache. The proposed fix addresses the wrong layer.

---

## 4. Amended Proposal

### What the evidence actually supports

Stripping non-SOLAR-implementable levers and bounding unverified claims:

**Defensible claim**: Path-reference dispatch (the HF1 mechanism) produces large per-request reductions in document injection tokens. The per-request normalized reduction is approximately −44.5% (not −89%). This is measured from two sessions of different scope, so confidence is MODERATE, not HIGH.

**Defensible claim**: Signal detection in `pre-tool-use.cjs` can block wasteful dispatch patterns IF the signal collection function is implemented. The enforcement architecture is valid. Current state: code defect (missing function).

**Not defensible as SOLAR deliverables**: tool restriction (L2), model tiering via frontmatter (L4), prompt cache prefix ordering (L5).

**Partially defensible**: Governor baton enrichment to eliminate subagent discovery turns (L3 reframed). This does not require a new hook; it requires instruction changes to the governor.

### Stripped-down valid proposal

| Lever                 | Reframed as                                                    | SOLAR deliverable type                     | Honest ET projection                                  |
| --------------------- | -------------------------------------------------------------- | ------------------------------------------ | ----------------------------------------------------- |
| L1 — Hard-fail signal | Fix `collectPreToolUseSignals()` stub + add to hardFailSignals | Change to template hooks                   | −5 to −10% gross regression prevention                |
| L3 — Baton enrichment | Governor includes known paths in dispatch baton (no new hook)  | Change to governor agent.md + baton schema | −10 to −20% subagent discovery turns                  |
| L1 + L3 combined      | Maintain HF1 gains + reduce discovery overhead                 | Template scaffold changes                  | −15 to −30% ET vs a regression-free post-HF1 baseline |

**The −55 to −70% stacked projection must be replaced with −15 to −30% until VS Code platform support for tool restriction and model tiering is available.**

The "rising to −80%+ with prompt-cache restoration" claim must be removed entirely from the SOLAR proposal — it is a VS Code platform roadmap item, not a SOLAR deliverable.

---

## 5. Specific Actionable Changes

The following are changes that ARE within SOLAR's control layer, map to specific deliverable types, and are not conditioned on VS Code platform features.

### 5A — Fix `collectPreToolUseSignals()` (Blocking)

**Target**: `mandarin-vite-react-ts/.github/hooks/common.cjs` (and `template/.github/hooks/common.cjs`)  
**What**: Implement the `collectPreToolUseSignals(input, config)` function and export it. The function should inspect the tool call input for:

- `DELTA_HANDOFF_SCHEMA_MISSING`: check if the tool name is `runSubagent` and the input payload lacks the required `compact-handoff-packet.schema.json` fields
- `DUPLICATE_READ_DETECTED`: check session state for whether the same file path has been read in the current session beyond `maxReadsPerFilePerSession`

Without this function, the `PreToolUse` hook is dead code — it crashes silently on every tool call.

**SOLAR deliverable**: Change to `template/.github/hooks/common.cjs`

### 5B — Update Template `solar.config.json` (Blocking for new installs)

**Target**: `template/.github/solar.config.json`  
**What**: The template config currently has only 5 fields (no `hardFailSignals`, no `maxReadsPerFilePerSession`, no `enforceDeltaForRedispatch`). New installs get a broken config that silently disables all guardrail enforcement. Add the full config schema matching `mandarin-vite-react-ts/.github/solar.config.json`:

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
  "hardFailSignals": [],
  "telemetry": { "modelMultipliersVersion": "v1" }
}
```

**SOLAR deliverable**: Change to `template/.github/solar.config.json` + sync to `solar-install.prompt.md`

### 5C — Governor Baton Enrichment (New, High Value)

**Target**: `template/.github/agents/orchestration-governor.agent.md`  
**What**: Add explicit instruction that EVERY `runSubagent` dispatch MUST include these fields in the baton packet:

- `ledger_stage`: current pipeline stage name
- `story_br_path`: relative path to the story BR doc
- `story_impl_path`: relative path to the story implementation doc
- `artifact_refs`: array of paths to artifacts the specialist will need
- `agents_md_section`: the specialist's own registry entry text (inline, not a path)

This eliminates the first 1–2 turns of every subagent session spent discovering where these files are. Unlike the session-start.cjs approach, this is a governor instruction change — no new infrastructure.

**SOLAR deliverable**: Change to `template/.github/agents/orchestration-governor.agent.md`

### 5D — Compact Handoff Schema in SKILL.md Templates

**Target**: All `template/.github/skills/*/SKILL.md` files  
**What**: Each SKILL.md's handoff/output section should explicitly reference `compact-handoff-packet.schema.json` and instruct the specialist to populate only delta fields. Currently this is under-specified — specialists know to produce an artifact but not the schema requirements.

**SOLAR deliverable**: Change to template SKILL.md files

### 5E — Remove or Reclassify Non-Implementable Levers

**Target**: `docs/work-logs/solar-token-optimization-proposal.md`  
**What**: Levers 2, 4, and 5 must be moved to a "Future / Depends on VS Code Platform" section with explicit conditions:

- L2 (tool restriction): blocked until VS Code agent mode supports per-agent toolset scoping
- L4 (model tiering): blocked until platform bugs #18873/#19402 are resolved AND VS Code provides deterministic model routing for `runSubagent`
- L5 (cache prefix): blocked until VS Code exposes prompt cache configuration to agent hooks

The executive summary's projected savings (−55 to −70%) must be revised to −15 to −30% for the SOLAR-implementable subset, with a note that the higher range requires platform support.

---

## 6. Outstanding Questions for the Proposal Author

1. **`collectPreToolUseSignals()` implementation**: Where is this function implemented? The exported function list in `common.cjs` does not include it. If HF2's signal detection relied on this function, and the function doesn't exist, what was actually measured?

2. **HF1 scope equivalence**: The post-HF1 session completed 11 subagents vs 20 pre-HF1. The proposal states these were both working on "Epic 16 documentation pipeline (14 output artifacts)." Were both sessions completing the same 14 artifacts? The 45% subagent reduction either means fewer agents were needed (efficiency gain) or fewer agents were run (incomplete work). The forensic reports should clarify.

3. **HF2 model selection mechanism**: How was Haiku 4.5 used in the post-HF2 Data Collector sessions? Was this from agent frontmatter (unreliable per P2 fix), manual VS Code selection, or BYOK config? The answer determines whether Lever 4 has any evidence at all.

4. **Provider consistency**: The proposal compares sessions across different providers (OpenAI vs Anthropic). No single same-provider controlled A/B comparison exists across all three hotfixes. Without a controlled run, the stacked projection is built on uncontrolled cross-provider data.

---

_Audit complete. Status: completed. Result: `verification-artifacts/20260524-token-optimization-adversarial-audit.md`._  
_Summary: The proposal's core HF1 finding (path-reference dispatch) is real and valuable, but the −89% headline is scope-confounded; normalized per-request improvement is −44.5%. Three of five proposed levers (L2, L4, L5) are not implementable by SOLAR without VS Code platform changes; Lever 3 requires reframing; Lever 1 has a code defect (`collectPreToolUseSignals()` not implemented in `common.cjs`) that silently disables the entire enforcement mechanism._
