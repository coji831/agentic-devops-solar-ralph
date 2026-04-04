# SOLAR-Ralph v4 Implementation Roadmap

**Source analysis:** `docs/research/notes/v4-feasibility-analysis.md`
**Date:** 2026-04-04
**Status:** Draft

---

## Step 1 — Dependency Reasoning

Sections from the feasibility analysis:

S1 — Lightweight Orchestration and Modular Governance Patterns
S2 — Designer-Implementer Firewalls and Security Protocols
S3 — Project-Agnostic Pipeline Cores and Dynamic Injection
S4 — Isolated Self-Improvement in .github/solar-system/
S5 — Interleaved Thinking and Context Compaction Strategies
S6 — Inquiry-First Protocol for Software Engineering Agents
S7 — Technical Implementation of Handoffs and Lifecycle Coordination

### Hard Dependencies

S4 creates .github/solar-system/ and all subdirectories.
Every other section deposits files into that tree:
S2 → solar-system/schemas/ (designer-output.schema.json, implementer-handoff.schema.json)
S3 → solar-system/context/ (context-tiers.md, compaction-policy.md, artifact-handle-pattern.md)
S5 → solar-system/context/ (effort-simulation.md, jit-loading-guide.md — extends S3 files)
S6 → solar-system/protocols/ (inquiry-first.md)
S7 → solar-system/schemas/ (handoff-types.md, per-type schema files)
→ solar-system/protocols/ (lifecycle-coordination.md, session-resumption.md)
S4 must be first. No other section can be scaffolded without it.

S3 defines compaction-policy.md.
S5 explicitly declares a dependency on "context tier model from S3" and
"compaction policy from S3" — compaction-policy.md is the shared artefact that
S5 refines. S3 must precede S5.

S2 creates solar-system/schemas/ (the directory and its first two schema files).
S7 adds additional schema files to the same directory and references the schema
naming pattern S2 establishes. S2 should complete scaffolding before S7 adds
dependent files, though concurrent work on independent schema files is safe.

S7 modifies .ai_ledger.template.md and registers SubagentStart/SubagentStop.
S1 adds governor skip logic and explicit agents: list that reads typed handoff
payloads introduced by S7. S7's governor instruction update should land before
S1 finalises the governor agent file to avoid double-edit conflicts.

### Risk-Based Ordering (sections modifying existing hooks rank higher for early validation)

High-risk (modifies files that fire on every agent turn):
S4 — modifies user-prompt-submit.cjs (learning-reminder removal) and
post-tool-use.cjs (ERRORS.md write instruction on failure)
S6 — modifies pre-tool-use.cjs to add Watch Mode permissionDecision: "ask" gate

Medium-risk (modifies existing agent or instruction files):
S2 — modifies design-planning-architect.agent.md and solar.instructions.md
S7 — modifies hooks.json (new hook registrations) and
orchestration-governor.agent.md and multiple agent.md files
S1 — modifies AGENTS.md (Router pipeline entry) and
orchestration-governor.agent.md (skip logic, agents: list)

Low-risk (additive: new config fields, documentation, new directories):
S3 — documentation only; zero modifications to existing hook or agent files
S5 — config fields and documentation; effort simulation is purely additive

Risk ordering rationale: S4 and S6 are the highest-risk sections because they
touch always-on hooks. Both should land early and be verified before downstream
sections add further hook complexity.

### Incremental Value (sections that unblock others rank higher)

S4 unblocks S2, S3, S5, S6, S7 (provides the shared directory).
S6 inquiry gate directly improves every feature pipeline's correctness.
S2 formalises the handoff contract that S7 extends.
S7 enables typed session resumption and lifecycle coordination that stabilises S1.
S1 reduces overhead for daily single-agent tasks.
S3 provides the mental model that S5 depends on.
S5 improves token efficiency — lower urgency until loop sessions routinely hit
context limits.

### Derived Implementation Order

S4 -> S6 -> S2 -> S7 -> S1 -> S3 -> S5

This matches the feasibility doc's Implementation Order exactly for sequence.
It differs in one phase-grouping decision:

Divergence: S3 is promoted from the feasibility doc's position 6 (between S1 and S5)
into Phase 1 alongside S4.

Reason for divergence: 1. S3 is zero-risk (documentation only) — co-locating it with S4 costs nothing. 2. S4 creates solar-system/context/ as part of its folder scaffold; S3 populates
exactly that subdirectory. Doing both in the same phase eliminates a partial
directory state. 3. S5 explicitly depends on S3's context tier model and compaction-policy.md.
Promoting S3 to Phase 1 makes it a first-class prerequisite rather than a
concurrent artefact in the same phase as its dependant. 4. The feasibility doc ranks S3 low on "incremental value" because it is
documentation, but that ranking measures working-system output, not
architectural enablement. S3 enables S5's design decisions — in particular,
the compaction threshold proxy metric (Open Decision S3) must be resolved in
Phase 1 or else the pre-compact.cjs script written in Phase 4 will be built
on an unreviewed assumption.

### Circular Dependency Check

S3 <-> S5: S5 depends on S3's compaction-policy.md. S3 does not reference S5.
One-directional. No circularity.

S2 <-> S7: S2 creates schemas/. S7 appends to schemas/. Same directory, sequential
access. One-directional. No circularity.

S1 <-> S7: S7 adds typed handoff fields that S1's governor reads. S1 does not
produce artefacts S7 requires. One-directional. No circularity.

---

## Step 2 — Milestone Roadmap

---

### Phase 1: Solar-System Foundation

**Goal:** Establish the isolated .github/solar-system/ directory, learning-capture
infrastructure, and the context tier documentation model that all subsequent
phases build on.

**Sections:**

- Isolated Self-Improvement in .github/solar-system/ (S4)
- Project-Agnostic Pipeline Cores and Dynamic Injection (S3)

**Decision Gate:** All of the following must be true before Phase 2 begins:

1. .github/solar-system/ directory exists with README.md explaining the isolation
   boundary.
2. LEARNINGS.md, ERRORS.md, and FEATURE_REQUESTS.md exist under
   solar-system/.learnings/.
3. session-start.cjs is registered in hooks.json and injects a LEARNINGS.md
   summary into at least one test session's additionalContext output.
4. user-prompt-submit.cjs modification is live (learning-reminder injection removed;
   ledger-state checks retained); regression test confirms existing pipeline
   start-of-turn behaviour is unchanged.
5. post-tool-use.cjs modification is live (ERRORS.md write instruction surfaces on
   tool failure); regression test confirms no false-positive failures on successful
   tool calls.
6. context-tiers.md, artifact-handle-pattern.md, and compaction-policy.md are
   written under solar-system/context/.
7. The compaction proxy metric Open Decision (S3) is resolved and recorded in
   compaction-policy.md before Phase 2 begins.

**Risk:** Hook modifications to post-tool-use.cjs and user-prompt-submit.cjs. Both
hooks fire on every agent turn. An incomplete removal of the learning-reminder
injection from user-prompt-submit.cjs could produce duplicate or missing ledger-state
messages. The post-tool-use.cjs ERRORS.md write instruction, if triggered on
non-failure conditions, will produce false error entries that pollute ERRORS.md.
Verify with explicit pass/fail tool call scenarios before closing this phase.

**Open Decisions to Resolve First:**

- S3 Compaction proxy metric: line count vs. completed-task count. Must be resolved
  to write compaction-policy.md with a concrete threshold value.
  [Recommended: Option B — task count. See resolution guide below.]

---

### Phase 2: Trust Enforcement and Safety Protocols

**Goal:** Enforce an inquiry gate that prevents implementation from starting without
grounded requirements, and formalise the Designer-Implementer output contract with a
schema and adversarial manifest.

**Sections:**

- Inquiry-First Protocol for Software Engineering Agents (S6)
- Designer-Implementer Firewalls and Security Protocols (S2)

**Decision Gate:** All of the following must be true before Phase 3 begins:

1. pre-tool-use.cjs Watch Mode modification is live and returns
   permissionDecision: "ask" for at least the tool patterns listed in
   solar.config.json watchModeToolPatterns; regression test confirms existing
   bypass-list logic is unaffected.
2. Watch Mode scope decision (S6) is resolved and enforced in the hook
   (loop-mode-only vs global).
3. solar-system/protocols/inquiry-first.md exists with minimum inquiry criteria
   (files examined, ambiguities resolved, plan approved flag).
4. .ai_ledger.template.md includes the Inquiry Gate section.
5. design-planning-architect.agent.md has been updated with the output format
   constraint referencing designer-output.schema.json.
6. solar-system/schemas/designer-output.schema.json and
   solar-system/schemas/implementer-handoff.schema.json exist.
7. solar-system/adversarial/skeleton-manifest.md is written with the agreed scope
   of patterns (5-8 or full catalog per Open Decision resolution).
8. A full Pipeline 4 (Feature) run completes without regression: Design Planning
   Architect produces schema-conformant output; Watch Mode fires only on qualifying
   tool patterns.

**Risk:** pre-tool-use.cjs modification (S6) is the highest-impact change in this
phase. Incorrect classification of a tool name as matching watchModeToolPatterns will
block safe read-only or test-run operations with an unexpected confirmation dialog.
Tool name patterns must be exact and tested against real tool call names before
deployment.

[ASSUMPTION: "high-risk tool calls" are defined by a string-pattern match against
tool call names as they appear in the VS Code Copilot hook input. If tool name formats
change across VS Code versions, watchModeToolPatterns must be updated accordingly.]

**Open Decisions to Resolve First:**

- S6 Watch Mode scope: global vs loop-mode only. Must be resolved before
  pre-tool-use.cjs is modified to avoid locking in the wrong default.
  [Recommended: Option B — loop-mode only.]
- S2 Output contract enforcement: trusted designer output vs adversarial-review
  gate on every plan. Must be resolved to set the schema-enforcement flow.
  [Recommended: Option A — trust with schema; route to Security Auditor only on
  failure or security-sensitive change.]
- S2 Adversarial manifest scope: 24-pattern catalog vs 5-8 pattern checklist.
  Must be resolved before skeleton-manifest.md is written.
  [Recommended: Option B — minimal 5-8 pattern checklist.]

---

### Phase 3: Inter-Agent Communication Infrastructure

**Goal:** Establish typed handoff schemas, lifecycle coordination hooks, and a
lightweight Router pipeline so the governor can dispatch single-agent tasks without
full pipeline overhead.

**Sections:**

- Technical Implementation of Handoffs and Lifecycle Coordination (S7)
- Lightweight Orchestration and Modular Governance Patterns (S1)

**Decision Gate:** All of the following must be true before Phase 4 begins:

1. SubagentStart and SubagentStop hooks are registered in hooks.json and verified:
   subagent-start.cjs reads the Handoff Payload field from the ledger and outputs
   it as additionalContext; subagent-stop.cjs blocks a subagent response that is
   missing required fields.
2. solar-system/schemas/handoff-types.md and per-type JSON schema files exist for
   scout_findings, dev_progress, review_result, and qa_result payloads.
3. solar-system/protocols/lifecycle-coordination.md and session-resumption.md are
   written; /memories/session/checkpoint.md is produced by a governor checkpoint
   write during at least one pipeline stage transition.
4. .ai_ledger.template.md Handoff Payload and Active Sub-tasks sections are live;
   any in-flight ledger instances are migrated or explicitly kept on the old
   template with a note.
5. AGENTS.md Router pipeline entry is written and tested for at least two signal
   types (e.g., quick-question, targeted-fix).
6. orchestration-governor.agent.md includes the conditional skip logic for Pipeline
   2 planner phase, the explicit agents: roster list, handoff payload read/write
   instruction for each pipeline stage transition, and the effort-preamble lookup
   table mapping effort: front matter values (Low/Medium/High/Max) to injected
   preamble text at delegation time. (OD-5 Option B: batched here to avoid a
   second edit of this file in Phase 4.)
7. Representative specialists (e.g., Implementation Specialist, Review Auditor)
   have handoffs: frontmatter with next-step transitions.
8. Worktree isolation Open Decision (S7) is resolved and recorded in
   lifecycle-coordination.md.

**Risk:** Ledger template changes affect all active and future work packages.
If the new Handoff Payload and Active Sub-tasks fields are introduced mid-session
on a live project, existing ledger entries will not have these fields and the
subagent-stop.cjs validation script may incorrectly block subagent responses.
A migration note or a conditional check in subagent-stop.cjs (tolerate missing
fields if ledger was created on old template) is required.

[ASSUMPTION: True filesystem-isolated parallel execution via git worktrees is deferred
unless a specific story requires it (per feasibility doc Open Decision S7 Option B
recommendation). The Router pipeline and parallel subagents use independent file
paths and ledger-based sub-task tracking for coordination.]

**Open Decisions to Resolve First:**

- S1 Router routing table: static signal-to-agent lookup table in AGENTS.md vs
  dynamic governor reasoning per turn. Must be resolved before the Router pipeline
  entry is written.
  [Recommended: Option A — static table.]
- S7 Parallel worktree isolation: implement git worktree management vs defer.
  Must be resolved and recorded in lifecycle-coordination.md; affects whether
  the governor needs worktree terminal command sequences.
  [Recommended: Option B — defer; use parallel subagents on independent paths.]

---

### Phase 4: Context Efficiency and Optimization

**Goal:** Operationalise effort simulation, JIT artifact loading, and governor-
triggered ledger compaction so that long-running loop sessions stay within context
limits without manual intervention.

**Sections:**

- Interleaved Thinking and Context Compaction Strategies (S5)

**Decision Gate:** All of the following must be true before this phase is considered
complete:

1. solar-system/context/effort-simulation.md is written with the four effort
   levels (Low / Medium / High / Max) and their instruction-text or front-matter
   encodings; the effort simulation encoding Open Decision (S5) is resolved.
2. solar-system/context/jit-loading-guide.md is written with line-count threshold
   and always-loaded vs always-referenced category list.
3. All agent.md files that require a non-default effort level carry the effort:
   front matter field (if Option B was chosen) or the corresponding instruction
   text preamble (if Option A was chosen).
4. pre-compact.cjs is registered in hooks.json and demonstrated to fire before at
   least one observed context auto-compaction event, writing
   /memories/session/pre-compact-state.md with active in-progress todos and
   ledger pipeline stage.
5. compaction-policy.md (written in Phase 1) has been updated with the threshold
   value aligned with the S3 Open Decision resolution and referenced by
   pre-compact.cjs.
6. orchestration-governor.agent.md includes the ledger compaction instruction
   triggered when task count exceeds the configured threshold.
7. solar.config.json carries the context.ledgerCompactionThreshold,
   context.artifactHandleEnabled, context.artifactSizeThresholdLines, and
   context.effort.\* fields.

**Risk:** Effort simulation is instruction-level only and cannot be
deterministically verified. An agent may produce a response that appears to follow
the effort level while not substantively doing so. The only observable signal is
response quality and thoroughness. Accept this limitation and document it as a known
constraint in effort-simulation.md rather than treating it as a blocking defect.

[ASSUMPTION: VS Code Copilot does not expose token count to hook scripts. The
ledger compaction threshold is measured in completed-task count (per S3 Open Decision
recommendation), not raw token count. If VS Code exposes a token count API in future
versions, update compaction-policy.md to switch to a token-count primary trigger with
task count as a fallback.]

[ASSUMPTION: Extended thinking activates automatically for Claude models in VS Code.
No .agent.md configuration is available to agent authors to control thinking budget
or effort at the API level.]

**Open Decisions to Resolve First:**

- S5 Effort simulation encoding: explicit instruction text per agent vs global
  effort: front matter field interpreted by governor. Must be resolved before
  agent.md files are updated and before jit-loading-guide.md references a
  specific effort level for large-context tasks.
  [Recommended: Option B — effort: front matter field; governor injects preamble
  at delegation time. This avoids editing every agent file when effort tuning
  changes.]

---

## Step 3 — Summary Table

| Phase | Sections                                        | Gate                                                                                                   | Highest Risk                                          | Status      |
| ----- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ----------------------------------------------------- | ----------- |
| 1     | S4 Isolated Self-Improvement, S3 Pipeline Cores | solar-system/ live; hooks verified; compaction-policy.md written; S3 Open Decision resolved            | post-tool-use.cjs / user-prompt-submit.cjs regression | Not Started |
| 2     | S6 Inquiry-First, S2 Designer-Implementer       | Watch Mode fires correctly; schema written; adversarial manifest written; Pipeline 4 regression clean  | pre-tool-use.cjs Watch Mode over-broad pattern match  | Not Started |
| 3     | S7 Handoffs/Lifecycle, S1 Lightweight Routing   | SubagentStart/Stop verified; typed schemas live; Router pipeline functional; governor roster declared  | ledger template migration breaking in-flight sessions | Not Started |
| 4     | S5 Interleaved Thinking / Compaction            | pre-compact.cjs fires; effort: field live; JIT guide written; governor compaction instruction in place | effort simulation phantom compliance (unverifiable)   | Not Started |

---

## Step 4 — Open Decisions Resolution Guide

Open decisions with cross-phase impact are marked. Decisions that affect only a single
phase section are included for completeness but flagged as local.

---

### OD-1: Router Routing Table Approach

**Source section:** S1 — Lightweight Orchestration
**Phase blocked:** Phase 3
**Cross-phase impact:** YES — Router pipeline entry in AGENTS.md is read by the
governor in every session; a dynamic routing decision would also affect how
typed handoff payloads (S7) are produced and consumed in Phase 3.
**Options:**
A) Static routing table: explicit signal-to-agent mappings written in AGENTS.md.
B) Dynamic: governor reasons about routing each turn without a fixed table.
**Recommended resolution:** Option A — static table.
Rationale: deterministic, auditable, lower risk of routing drift across sessions.
A static table also makes it straightforward for the SubagentStart hook (S7) to
inject the correct typed context for the dispatched agent without needing to
infer which agent will be called.
**Owner:** Architect

---

### OD-2: Output Contract Enforcement Approach

**Source section:** S2 — Designer-Implementer Firewalls
**Phase blocked:** Phase 2
**Cross-phase impact:** NO — enforcement scope is confined to the S2 design-to-
implementation handoff. Does not affect Phase 3 or Phase 4 schemas.
**Options:**
A) Trust designer output that follows schema instructions; review only on
escalation or when security-sensitive changes are detected.
B) Security Auditor reviews every Design Planning Architect output before any
implementation agent is invoked.
**Recommended resolution:** Option A.
Rationale: Option B adds a Security Auditor call on every pipeline, which doubles
latency for standard feature work. Schema-based instruction compliance is
sufficient for initial v4; escalate to auditor only on schema validation failure
or when solar.config.json requireDesignBeforeImpl is true and the ledger has no
approved design entry.
**Owner:** Architect

---

### OD-3: Adversarial Manifest Scope

**Source section:** S2 — Designer-Implementer Firewalls
**Phase blocked:** Phase 2
**Cross-phase impact:** NO — manifest is confined to solar-system/adversarial/;
does not constrain Phase 3 or Phase 4 artefacts.
**Options:**
A) Full 24-pattern vulnerability catalog (Elder Plinus methodology).
B) Minimal 5-8 pattern checklist covering prompt injection and persona hijacking.
**Recommended resolution:** Option B.
Rationale: A full 24-pattern catalog is research-grade effort not justified by the
current VS Code Copilot attack surface. Begin with a 5-8 pattern checklist; expand
only if prompt injection incidents are observed in production use.
**Owner:** Architect

---

### OD-4: Compaction Proxy Metric

**Source section:** S3 — Project-Agnostic Pipeline Cores
**Phase blocked:** Phase 1 (compaction-policy.md must carry a concrete threshold),
Phase 4 (pre-compact.cjs uses this metric).
**Cross-phase impact:** YES — Phase 1 writes compaction-policy.md with the chosen
metric; Phase 4 pre-compact.cjs script and solar.config.json
context.ledgerCompactionThreshold field both depend on that same metric.
A metric change after Phase 1 requires updates to both compaction-policy.md and
the Phase 4 hook script.
**Options:**
A) Trigger compaction at N lines in .ai_ledger.md.
B) Trigger at N completed tasks in the ledger.
**Recommended resolution:** Option B — completed-task count.
Rationale: task count is semantically stable regardless of formatting verbosity.
Line count varies when ledger entries are verbose (e.g., long handoff payloads).
A task-count threshold of 10 completed tasks is a reasonable starting default;
adjust via context.ledgerCompactionThreshold after observing real session patterns.
**Owner:** Architect
**Action required in Phase 1:** Record chosen metric and initial threshold value in
compaction-policy.md before closing Phase 1 gate.

---

### OD-5: Effort Simulation Encoding

**Source section:** S5 — Interleaved Thinking and Context Compaction
**Phase blocked:** Phase 4
**Cross-phase impact:** YES — resolved by batching the governor update into Phase 3.
**RESOLVED: Option B — effort: front matter field.**
Governor maps the field to an injected preamble at delegation time. The
governor effort-preamble lookup instruction has been added to Phase 3 gate
item 6 so that orchestration-governor.agent.md is updated in a single edit
during Phase 3, not reopened in Phase 4.
**Options:**
A) Encode effort level as explicit instruction text in each agent.md.
B) Add effort: front matter field to agent.md; governor maps the field to an
injected preamble at delegation time. [CHOSEN]
[ASSUMPTION: The effort: field is instruction-level only, not an API parameter.
Compliance is not enforced by VS Code; it is a governor-mediated convention.]
**Owner:** Architect
**Action completed:** Governor effort-preamble lookup batched into Phase 3
gate item 6.

---

### OD-6: Watch Mode Scope

**Source section:** S6 — Inquiry-First Protocol
**Phase blocked:** Phase 2
**Cross-phase impact:** NO — Watch Mode is a pre-tool-use.cjs concern confined to
Phase 2. Phases 3 and 4 do not add further pre-tool-use.cjs modifications.
**Options:**
A) Watch Mode fires globally on any destructive tool call pattern regardless of
session type.
B) Watch Mode fires only when Session-Type: loop is active in the ledger.
**Recommended resolution:** Option B — loop-mode only.
Rationale: avoids friction in planning/chat sessions where destructive-pattern
matches (e.g., delete operations during cleanup tasks) are expected and
pre-approved. Autonomous loop execution is the highest-risk context and is the
correct scope for requiring user confirmation.
**Owner:** Governor / Installer (requires solar.config.json
hooks.preToolUse.watchModeEnabled and pre-tool-use.cjs to read Session-Type from
ledger before applying the gate)

---

### OD-7: Parallel Worktree Isolation

**Source section:** S7 — Technical Implementation of Handoffs and Lifecycle
**Phase blocked:** Phase 3
**Cross-phase impact:** YES — If Option A (implement worktrees) is chosen, Phase 4's
JIT loading guide (S5) must account for the case where artifacts reside in a
worktree path rather than the main workspace path. Deferring (Option B) removes
this complication from Phase 4 entirely.
**Options:**
A) Implement worktree creation/teardown as governor terminal-command sequences
for parallel sub-tasks that edit overlapping paths.
B) Defer worktree isolation; use native parallel subagents on independent paths
with ledger-based Active Sub-tasks tracking for coordination.
**Recommended resolution:** Option B — defer.
Rationale: parallel subagent execution is now natively supported and works without
worktrees for tasks on independent file paths, which covers the large majority of
SOLAR pipeline sub-tasks. Worktree management adds significant governor complexity
(create, switch, merge, teardown) without proportionate benefit given that
concurrent edits to the same file path are rare in structured pipelines.
Revisit if a specific story requires two agents editing the same file simultaneously.
**Owner:** Architect
**Action required in Phase 3:** Record deferral decision in
solar-system/protocols/lifecycle-coordination.md with a clear trigger condition
for when to reconsider (e.g., observed write conflict in a parallel subagent run).
