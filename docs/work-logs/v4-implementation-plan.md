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
   solar-system/learnings/.
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

### Phase 5: Gap Closure — Feedback Items Not Covered by Phases 1-4

**Prerequisite:** Phase 5 is executable only after all Phase 1-4 decision gates
are closed. S8-S12 are additive changes only — no Phase 1-4 artefact is deleted
or overwritten. Files already modified by Phases 1-4 that Phase 5 also touches are
called out explicitly in each section below with a "prior-phase owner" note.

**Goal:** Close the five feedback items FB-3, FB-6, FB-12, FB-15, and FB-17 that
were not fully addressed by Phases 1-4: repo-adaptive setup with user-verification
gate (FB-3); AGENTS.md baseline-only redesign with JIT pipeline loading (FB-6);
project-unbiased agent and prompt defaults (FB-12); format-safe output with adapted
template enforcement (FB-15); and per-session SOLAR activity logging (FB-17).
Sections S8-S12 are gap-closure work only and have no corresponding feasibility
analysis section. VS Code native log views (Agent Debug Logs, MCP Output log) are
read-only UI surfaces that cannot be written to by hooks; the per-session JSON file
in S12 is the mechanism for FB-17.

**Sections:**

- S8 — Repo-Adaptive Setup with User-Verification Gate (FB-3)
- S9 — AGENTS.md Baseline-Only Redesign with JIT Pipeline Loading (FB-6)
- S10 — Project-Unbiased Agent and Prompt Defaults (FB-12)
- S11 — Format-Safe Output with Adapted Template Enforcement (FB-15)
- S12 — Per-Session SOLAR Activity Log (FB-17)

---

#### S8: Repo-Adaptive Setup with Greedy Capture and Soft Nudge

**Clarification:** This is a setup-stage improvement, not a blocking gate. The
full setup flow (`/solar-setup-full`, `/solar-setup-quick`, `/solar-setup-scan-repo`

- `/solar-setup-core-config`) already exists and runs freely. The FB-3 feedback
  asks for "extract all and request user to verify" — the scan already emits
  `INFERRED:` markers for assumed values, but the scan agent's default posture is
  to omit fields it is not confident about, and the Step 3 report does not tell the
  user to review those markers before running setup.

S8 fixes both gaps: (1) instruct the scan agent to always capture a value for
every profile field, flagging confidence rather than skipping; (2) add a soft
review nudge to the scan's Step 3 report. No blocking gate, no config flag, no
new files. The user can correct `solar-project-profile.json` and re-run setup
at any time.

**Implementation Skeleton:**

Files to create or modify:

- `.github/agents/solar-bootstrap.agent.md` — MODIFY: strengthen the capture
  posture in the Critical Constraints block (currently constraint #6 says
  "INFERRED VALUES: If a value is an assumption, write `INFERRED: [value]`"):
  replace with: "GREEDY CAPTURE: Never omit a profile field because evidence is
  ambiguous. Always emit a value — use `INFERRED: [value]` for assumed values and
  `LOW-CONFIDENCE: [value]` for values with weak signal. A profile that
  over-captures with confidence flags is preferable to a sparse profile;
  the user review step is the quality gate."

- `.github/prompts/solar-setup-scan-repo.prompt.md` — MODIFY: in the Step 3
  Report block, add one line to the "Next steps" output:
  "If `INFERRED:` or `LOW-CONFIDENCE:` values appear above, review
  `.github/solar-project-profile.json` and correct before or after running setup."

Config / frontmatter fields needed: none

Isolation: `.github/` only; no new files or directories created

---

#### S9: AGENTS.md Baseline-Only Redesign with JIT Pipeline Loading

**Clarification:** Phases 1-4 regressed this feedback item — Phase 3 gate #5
wrote a full Router pipeline body directly into AGENTS.md, making it larger and
more pipeline-specific, not simpler. FB-6 ("AGENTs.md need to be more simple and
generic") is not partially addressed; it is unaddressed by Phases 1-4. S9 is the
full closure.

AGENTS.md is platform-injected on every agent turn, so every line equals
persistent token cost regardless of which pipeline is active. Anthropic's routing
workflow pattern (classify → dispatch to specialized handler) makes the correct
split explicit: the governor's existing `<pipeline_selection>` block already serves
as the lightweight index (signal → pipeline name); it does not need AGENTS.md for
this. The full stage bodies are only needed once per session, only for the selected
pipeline. All stage detail therefore moves to per-pipeline files loaded JIT.

AGENTS.md is reduced to the operating contract only: purpose, precedence, roles,
session-type table. Nothing executable remains in it. Project-level fine-tuning
(skip a step, add a stage) is applied by modifying the per-pipeline file, not
AGENTS.md.

**Implementation Skeleton:**

Files to create or modify:

- `.github/AGENTS.md` — REDESIGN [prior-phase owner: Phase 3 gate #5 wrote the
  Router pipeline entry]: keep only:
  1. S.O.L.A.R. 5-layer purpose statement (already in AGENTS.md lines 3-14)
  2. Instruction precedence list (already present)
  3. Core role roster (one line per role, name + one-sentence purpose only)
  4. Session-Type reference table (chat / loop / manual-test)
  5. Execution mode (chat vs loop — one sentence each)
     Remove: all Pipeline 0-4 stage bodies, Mandatory Delegation Matrix, Write-Back
     Rule body (move to solar.instructions.md), Operating Artifacts detail
     (move to solar.instructions.md), Pipeline Contracts section header and body.
     Do NOT add a "pipeline definitions: load from..." pointer line — the
     governor's `<pipeline_selection>` block already serves as the index; a
     redundant pointer in AGENTS.md adds noise without value. Target: 40-60 lines.
     Migration note: the Router pipeline body written by Phase 3 is NOT deleted —
     it migrates intact to `pipeline-0-router.md` in the step below.

- `.github/solar-system/pipelines/` — NEW directory: one file per pipeline.
  Each file contains the full stage definition currently in AGENTS.md:
  - `pipeline-0-router.md` — Router pipeline (signal types, routing table, bypass conditions)
  - `pipeline-1-knowledge.md`
  - `pipeline-2-simple-fix.md`
  - `pipeline-3-bug-fix.md`
  - `pipeline-4-feature.md`
    These files are NOT auto-loaded. The governor reads the matching file when it
    selects a pipeline. Pipeline files are generic — no project-specific commands
    or stack references. Fine-tuning for a specific project belongs in
    `.github/solar-system/` override files, not in these base pipeline files.

- `.github/agents/orchestration-governor.agent.md` — MODIFY [prior-phase owners:
  Phase 3 gate #6 added conditional skip logic, agents: roster, handoff payload
  read/write, and effort-preamble table; Phase 4 gate #6 added ledger compaction
  instruction — this is the third and final edit to this file]:
  Two targeted changes:
  1. In `<pipeline_selection>`, replace the instruction _"execute that pipeline's
     stage sequence from `.github/AGENTS.md` in order"_ with: _"read
     `.github/solar-system/pipelines/<pipeline-name>.md` to get the stage sequence,
     then execute it in order."_ This is a one-line replacement; the
     signal-to-pipeline mapping entries below it are unchanged.
  2. In the tiered-context gate table, add a new row:
     `| All pipelines (except Knowledge) | Read matching pipeline file from solar-system/pipelines/ BEFORE first agent call |`
     and update the note at the bottom of the gate from "do NOT read AGENTS.md
     explicitly" to "do NOT read AGENTS.md explicitly; DO read the selected
     pipeline file from solar-system/pipelines/ before stage 1."
     All prior-phase content (skip logic, handoff read/write, compaction) is
     preserved; only these two targeted replacements are made.

Folder changes (if any):

```
.github/
  solar-system/
    pipelines/
      pipeline-0-router.md
      pipeline-1-knowledge.md
      pipeline-2-simple-fix.md
      pipeline-3-bug-fix.md
      pipeline-4-feature.md
```

Config / frontmatter fields needed: none

[ASSUMPTION: Governor can locate and read the pipeline file at delegation time using
the `read_file` tool. No hook automation is required for JIT pipeline loading;
the governor instruction is sufficient.]
[ASSUMPTION: Pipeline files contain generic, stack-agnostic stage definitions only.
Any project-specific step (e.g., run npm test) is injected via solar-system/
override files resolved at setup time, not hardcoded into pipeline files.]

Isolation: SOLAR-only (AGENTS.md baseline, pipeline files)

---

#### S10: Project-Unbiased Agent and Prompt Defaults

**Clarification:** The target is to make every SOLAR agent and prompt work correctly
out-of-the-box for any project without assuming a specific stack (e.g., npm, React,
Prisma). A user who installs SOLAR without running the full setup should still get
useful, correct agent behavior. Stack-specific adaptation is added later via
custom solar-system/ override instruction files, reducing the need to modify
agent or prompt files directly.
**Implementation Skeleton:**

Files to create or modify:

- All `.github/agents/*.agent.md` — AUDIT: identify any hard-coded technology
  references (npm, TypeScript, ESLint, Prisma, React, etc.) in instruction bodies.
  For each:
  - If the reference is a default example, replace with a generic placeholder
    token (e.g., `[verify-command]`, `[lint-command]`, `[test-command]`)
  - If the reference is a stack-specific step, move it to a companion
    `.github/solar-system/pipelines/` override entry or
    `.github/instructions/*.instructions.md` with `applyTo` glob
  - Retain technology-neutral behavioural rules (e.g., "run verification before
    claiming progress") unmodified.

- `docs/guides/prompt-authoring-guide.md` — ADD: "Project-Unbiased Writing Rules"
  section:
  - No stack names, package managers, or framework paths in agent instruction bodies
  - Use token placeholders for commands; resolved by approved-profile.md injection
  - Each agent must cover at least 3 scenario types (new feature / bug fix /
    refactor) — single-use-case agents belong in custom solar-system/ workflows
  - Fine-tuning a specific stack: create a companion instruction file with
    `applyTo` glob; do NOT edit the base agent file

Config / frontmatter fields needed: none (audit and guideline update only)

[ASSUMPTION: Agent audit scope is limited to `.github/agents/*.agent.md` files.
Skill SKILL.md files are not modified in this phase — they contain methodology
rather than stack-specific commands, so bias is lower.]

Isolation: SOLAR-only (agent file cleanup and guide update)

---

#### S11: Format-Safe Output with Adapted Template Enforcement

**Clarification:** The feedback is: _"implementor/doc writer sometimes output
without keeping format or wrong position."_ This is a target-repo problem, not a
SOLAR setup problem. When agents write or update files in the target repo — code
comments, implementation docs, BR files, README sections — they sometimes:

- Invent their own section structure instead of following the repo's existing template
- Place content in the wrong section of an existing file
- Reorder or remove sections they should not touch

The fix is instruction-level enforcement on implementation and doc agents: before
writing to any file in the target repo, the agent MUST read the full current file
and identify where the new content belongs. If creating a new file, the agent MUST
check whether the target repo's docs contain a matching template before inventing
structure. This enforcement applies specifically to agents that write target-repo
artefacts (Implementation Specialist, Docs Curator, Design Planning Architect).
It does NOT apply to SOLAR's own internal files.

**Implementation Skeleton:**

Files to create or modify:

- `.github/solar-system/patterns/output-position-contract.md` — NEW: defines the
  write-safe rules enforced on all agents that modify target-repo files:
  - Before modifying an existing file: read the full current file; identify all
    existing section headers and their order; write new content only inside the
    correct matching section; do NOT add, remove, or reorder sections unless
    explicitly instructed by the user or the design doc.
  - Before creating a new file: search the target repo for an existing template
    of the same doc type (e.g., `docs/templates/`); if found, use it as the
    skeleton; if not found, ask the user or Design Planning Architect for a
    skeleton — do NOT invent structure.
  - Wrong-position rule: if the correct section for the new content cannot be
    identified with confidence, STOP and ask — do not place content in an
    approximate or nearby section.

- `.github/agents/implementation-specialist.agent.md` (and other agents that write
  target-repo files: Docs Curator, Design Planning Architect) — ADD:
  `<output_contract>` XML block enforcing the write-safe rules:
  - Read target file in full before any edit.
  - Identify target section before writing.
  - Match existing template if creating a new file.
  - Wrong position = formatting defect; stop and ask rather than guess.
    No prior-phase edits to these files in Phases 1-4.

- `.github/instructions/solar.instructions.md` — MODIFY [prior-phase owner:
  Phase 2 (S2) added inquiry-first and schema-enforcement sections — this is the
  second edit; Phase 2 content is preserved]: ADD "Format Safety Rules" section
  as a new section after the existing Phase 2 content:
  - All agents MUST read the target file before modifying it.
  - All agents MUST place content in the correct existing section — not an
    approximate one.
  - New file creation requires a matching template from the target repo; absent
    one, ask before proceeding.
  - Wrong-position output is a formatting defect and a review finding.

Config / frontmatter fields needed: none (instruction-level enforcement only)

[ASSUMPTION: The `<output_contract>` block is a VS Code agent instruction convention.
Compliance is verified by review agents reading output-position-contract.md during
their review step. No hook enforcement is needed.]
[ASSUMPTION: "Target repo" means the user's project files (docs/, src/, etc.), not
SOLAR's own .github/ artefacts. SOLAR internal file writes are governed by their
own agent instructions and are out of scope for S11.]

Isolation: SOLAR-only (enforcement instructions only; no target-repo files modified)

---

#### S12: Per-Session SOLAR Activity Log

**Clarification:** Phase 1 captures errors in ERRORS.md (persistent, cross-session).
This section adds a per-session activity log: a new JSON file created at session
start and appended by hooks on every SOLAR tool call event. It records what happened
inside SOLAR (which tools fired, which agents were delegated to, which files were
written, any errors) so that sessions can be monitored and debugged after the fact.
Format is JSON for token efficiency when loading the log back into context for
analysis. VS Code Agent Debug Logs and MCP Output Log are native UI views (read-only,
not hook-writable) — they supplement this log but do not replace it.

**Implementation Skeleton:**

Files to create or modify:

- `.github/hooks/session-start.cjs` — MODIFY (from Phase 1 — already creates this
  hook): add session log creation. At session start, create a new log file at
  `.github/solar-system/logs/session-<ISO-timestamp>.json`:

  ```json
  { "session": "<timestamp>", "events": [] }
  ```

  Write the path of the current log file to a temp ref:
  `.github/solar-system/logs/.current-session`.

- `.github/hooks/post-tool-use.cjs` — MODIFY [prior-phase owner: Phase 1 gate #5
  added ERRORS.md write instruction on tool failure — this is the second edit;
  Phase 1 ERRORS.md logic is preserved and runs first]: after existing ERRORS.md
  logic, if `config.logging.sessionLog.enabled` is true, read `.current-session`
  to get the active log file path, then append one JSON event object:

  ```json
  {
    "t": "<ISO-timestamp>",
    "tool": "<tool-name>",
    "file": "<file-path-if-any>",
    "ok": true|false,
    "note": "<error-message-if-failed>"
  }
  ```

  Append to the `"events"` array. Keep the entry compact — no full file contents,
  no tool input payloads. Fields: timestamp, tool name, affected file path (if
  readable from tool output), success/fail boolean, error note on failure only.

- `.github/hooks/stop.cjs` — MODIFY: on session stop, append a final event:

  ```json
  { "t": "<ISO-timestamp>", "tool": "SESSION_END", "ok": true }
  ```

  then clear `.current-session`.

- `.github/solar-system/logs/` — NEW directory (gitignored): holds per-session
  log files. Add `.github/solar-system/logs/*.json` to `.gitignore`.

- `.github/solar-system/learnings/LOG-SOURCES.md` — NEW: reference table for all
  available log sources and how to use them:
  | Source | Location | Access | Write-back target |
  |---|---|---|---|
  | Session Log | solar-system/logs/session-\*.json | read_file | ERRORS.md (on failure events) |
  | ERRORS.md | solar-system/learnings/ERRORS.md | Phase 1 auto | Self |
  | Agent Debug Logs | VS Code Chat -> ... -> Show Agent Debug Logs | UI only | ERRORS.md (manual) |
  | MCP Output Log | Command Palette -> MCP: List Servers -> Show Output | UI only | ERRORS.md (manual) |

- `.github/solar-system/README.md` — MODIFY [prior-phase owner: Phase 1 gate #1
  created this file — this is the second edit]: add `logs/` entry to the isolation boundary section
  alongside the existing project-profile/ entry. All prior content preserved.

Folder changes (if any):

```
.github/
  solar-system/
    logs/
      .current-session    (temp ref, cleared on stop)
      session-<ts>.json   (gitignored, per-session)
```

Config / frontmatter fields needed:

- `solar.config.json` -> `logging.sessionLog.enabled: boolean` — master toggle
  for per-session log writing (default: true)
- `solar.config.json` -> `logging.sessionLog.path: string` — log directory path
  (default: `.github/solar-system/logs/`)
- `solar.config.json` -> `logging.sessionLog.maxFiles: number` — maximum number
  of session log files to retain before oldest is deleted on new session start
  (default: 20)

[ASSUMPTION: VS Code hook scripts can write files using Node.js fs module —
confirmed by existing hook implementations (post-tool-use.cjs, session-start.cjs).
The tool input payload is not logged (only tool name + file path) to keep log
files compact.]
[ASSUMPTION: ISO timestamp for the filename is generated via
`new Date().toISOString().replace(/[:.]/g, "-")` — avoids filesystem-illegal
characters on Windows.]

Isolation: SOLAR-only (logs/ is gitignored and never referenced by pipeline agents
during active execution)

---

**Decision Gate:** All of the following must be true before Phase 5 is considered
complete:

1. `solar-bootstrap.agent.md` has the greedy-capture constraint in place (never
   omit a field, emit `INFERRED:` or `LOW-CONFIDENCE:` instead); the scan Step 3
   report includes the soft nudge directing the user to review
   `solar-project-profile.json` if flagged values appear. Setup commands run
   freely — no blocking gate.
2. AGENTS.md is reduced to 40-60 lines containing only the 5-layer baseline,
   instruction precedence, role roster, and session-type table (no pipeline bodies,
   no Pipeline Contracts section, no pointer line — governor `<pipeline_selection>`
   block serves as the index); all Pipeline 0-4 stage bodies exist as generic,
   stack-agnostic files in solar-system/pipelines/\*.md; governor
   `<pipeline_selection>` instruction references the pipeline files and the
   tiered-context gate table includes the pipeline file read row.
3. All agent.md files pass the stack-agnostic audit (no hard-coded npm/React/
   Prisma/ESLint references in instruction bodies); prompt-authoring-guide.md has
   the Project-Unbiased Writing Rules section.
4. output-position-contract.md exists with write-safe rules (read before edit,
   correct-section placement, template-match before create); Implementation
   Specialist, Docs Curator, and at least one other agent carry the
   `<output_contract>` block; solar.instructions.md has the Format Safety Rules
   section. SCOPE: target-repo file writes only — not SOLAR internal artefacts.
5. session-start.cjs creates a new per-session JSON log in solar-system/logs/;
   post-tool-use.cjs appends compact JSON events to the active log; stop.cjs
   writes SESSION_END and clears .current-session; LOG-SOURCES.md exists.

**Risk:** S9 AGENTS.md redesign is the highest-risk item. Removing pipeline stage
bodies from AGENTS.md and moving them to JIT-loaded files changes the governor's
information access pattern. If the governor does not consistently load the pipeline
file before executing a stage, it will operate with incomplete stage knowledge.
The pipeline-load instruction in orchestration-governor.agent.md is the single
point of failure — it must be unambiguous and tested with a full Pipeline 4 run
before this phase closes.

S12 hook modifications touch stop.cjs, which is the loop-continuation enforcement
hook. Any error in the stop.cjs modification could silently disable loop enforcement.
Verify loop continuation still fires after stop.cjs changes by running a
two-step loop session and confirming the exit-block message still appears.

**Open Decisions to Resolve First:**

- S9 AGENTS.md split approach: remove pipeline bodies from AGENTS.md in place
  (single edit) vs. write pipeline files first, verify governor can load them,
  then remove from AGENTS.md (two-step). Must be resolved before any AGENTS.md
  edits.
  [Recommended: two-step — write pipeline files first, add governor load
  instruction, verify one full pipeline run, then remove pipeline bodies from
  AGENTS.md. This ensures there is never a moment where pipeline detail is
  inaccessible.]

- S12 log file rotation: delete oldest file when maxFiles limit is reached vs.
  keep all and warn. Must be resolved before session-start.cjs is written.
  [Recommended: delete oldest on session start if count exceeds maxFiles;
  silent deletion, no warning — log files are diagnostic, not auditable records.]

---

## Step 3 — Summary Table

| Phase | Sections                                        | Gate                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Highest Risk                                                                             | Status      |
| ----- | ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ----------- |
| 1     | S4 Isolated Self-Improvement, S3 Pipeline Cores | solar-system/ live; hooks verified; compaction-policy.md written; S3 Open Decision resolved                                                                                                                                                                                                                                                                                                                                                              | post-tool-use.cjs / user-prompt-submit.cjs regression                                    | Not Started |
| 2     | S6 Inquiry-First, S2 Designer-Implementer       | Watch Mode fires correctly; schema written; adversarial manifest written; Pipeline 4 regression clean                                                                                                                                                                                                                                                                                                                                                    | pre-tool-use.cjs Watch Mode over-broad pattern match                                     | Not Started |
| 3     | S7 Handoffs/Lifecycle, S1 Lightweight Routing   | SubagentStart/Stop verified; typed schemas live; Router pipeline functional; governor roster declared                                                                                                                                                                                                                                                                                                                                                    | ledger template migration breaking in-flight sessions                                    | Not Started |
| 4     | S5 Interleaved Thinking / Compaction            | pre-compact.cjs fires; effort: field live; JIT guide written; governor compaction instruction in place                                                                                                                                                                                                                                                                                                                                                   | effort simulation phantom compliance (unverifiable)                                      | Not Started |
| 5     | S8-S12 Gap Closure (FB-3,6,12,15,17)            | scan greedy-capture constraint live + soft nudge in Step 3 report; AGENTS.md reduced to 40-60 line operating contract (no pipeline bodies, no pointer line); JIT pipeline files in solar-system/pipelines/ generic and stack-agnostic; governor `<pipeline_selection>` instruction + tiered-context gate updated; agents pass bias-free audit; output-position-contract.md + `<output_contract>` blocks in agents; per-session JSON log created by hooks | AGENTS.md JIT regression on Pipeline 4; stop.cjs loop enforcement intact after S12 edits | Not Started |

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
