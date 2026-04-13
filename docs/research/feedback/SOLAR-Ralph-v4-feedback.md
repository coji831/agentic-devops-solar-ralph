# SOLAR-Ralph v4 Feedback (Epic 16 Cycle Test)

**Test Context:** Full feature implementation cycle (Epic 16) in mandarin-vite-react-ts repository  
**Test Duration:** 72 hours of development time, 8+ agents, 15+ tasks  
**Date:** April 2026  
**Status:** Production feedback compilation

---

## Document Structure

1. **[Consolidated Feedback](#consolidated-feedback)** — 51 draft items organized into 14 sections
2. **[v4 Features Status Table](#v4-features-status-table)** — 31 features with working/failed/obsolete status
3. **[Draft Mapping Table](#draft-mapping-table)** — Maps original 51 draft items to organized sections (for tracking)

---

## Executive Summary

SOLAR-Ralph v4 successfully orchestrated a complex epic implementation with several strong patterns (pipeline recognition, verification artifacts, deliverable templates) but revealed critical gaps in orchestrator behavior, agent specialization, and state management.

**Key Wins:**

- ✅ Pipeline recognition working well
- ✅ Verification artifacts effective as data central
- ✅ Deliverable template handoffs smooth

**Critical Issues:**

- ❌ Orchestrator doing too much (reading files, making decisions, writing ledger)
- ❌ No loop invocation mechanism
- ❌ Agent role boundaries blur (curator/implementor/planner overlap)
- ❌ Memory/ledger/learning storage unclear

**Feature Verification Results (Epic 16 test):**

- **Working:** 9/31 features (29%) — Setup, pipelines, handoff schemas
- **Partial/Not Visible:** 12/31 features (39%) — Foundation, lifecycle hooks
- **Broken:** 10/31 features (32%) — Inquiry gate, learning capture, session logs
- **Highest Priority Fixes:** Inquiry gate (bypassed), learning capture (dead), session logging (non-functional)

---

<a id="consolidated-feedback"></a>

# Part 1: Consolidated Feedback

_51 draft feedback items organized into 14 problem categories. See [Draft Mapping Table](#draft-mapping-table) for original draft item numbers._

---

## 1. Setup & Installation

### 1.1 Template Deployment Issues

**Source:** #1, #2, #29

**Problem:** Installer renaming templates to working files fails; duplicate solar folders created; [FILL IN] placeholders not replaced after setup.

**Impact:** Manual post-install fixes required; unclear which solar folder is canonical.

**Recommendation:**

- Replace `rename` with merge logic (read template → apply placeholders → write to destination)
- Consolidate to single `.github/solar-system/` folder
- Add setup verification step to detect unfilled placeholders

---

## 2. Architecture & Workflow Design

### 2.1 Workflow vs Pipeline Model

**Source:** #3, #4, #21, #42

**Problem:** Deep pipeline architecture (0→1→2→3→4) is rigid; unclear whether workflows belong in `.github/` or `solar-system/`; pipeline notifications verbose but effective.

**What's Working:** Pipeline recognition for features; stage notifications provide good visibility.

**Recommendation:**

- **Migrate to workflow-based architecture:** Replace numbered pipelines with composable workflows (different levels, intertwined)
- **Simpler gap detection:** Easier to spot missing workflows and suggest additions
- **Location:** Move workflows to `.github/solar-system/workflows/`
- **Reuse notifications:** Extract notification pattern into workflow step template

---

## 3. Orchestrator Core Issues

### 3.1 Orchestrator Doing Too Much

**Source:** #22, #38, #46, #51

**Problem:** Orchestrator reads files, gathers information, makes tactical decisions instead of delegating. This floods context, limits model upgrade options, causes track loss during extensive cycles.

**Impact:** Can't upgrade to higher-context model (cost prohibitive); loses focus during multi-cycle bug fixes.

**Recommendation:**

- **Minimize tool use:** Orchestrator only delegates, monitors ledger, routes decisions
- **Reader agent:** Dedicated collector gathers information, provides summary
- **Programmatic workflow init:** Force workflow selection/creation before any delegation
- **Sub-agent communication:** Via handoff templates and ledger only, orchestrator reads results not raw data

### 3.2 Workflow Uncertainty & User Guidance

**Source:** #5, #6, #49

**Problem:** Orchestrator doesn't ask when workflow unclear; doesn't hint user when gaps spotted mid-task.

**Recommendation:**

- **Pre-flight check:** Ask user to confirm workflow if ambiguous
- **Gap detection prompt:** "This task requires [missing capability]. Add workflow or adjust scope?"
- **Feedback loop:** Actively check for user input to update instructions/workflows/memory

### 3.3 Loop Invocation Missing

**Source:** #9, #10

**Problem:** Orchestrator doesn't know when to invoke SOLAR loop; no mechanism to elevate workflow to loop mode; loop tracking in ledger undefined.

**Recommendation:**

- **Loop flag:** Workflow metadata `loop: true` triggers loop mode
- **Ledger section:** Add `## Active Loops` with loop ID, workflow, iteration count, exit condition
- **Exit conditions:** Define max iterations, success criteria, timeout

### 3.4 Ledger Format Errors

**Source:** #11, #15

**Problem:** Orchestrator writes wrong session type to ledger; doesn't reset ledger before new workflow.

**Recommendation:**

- **Ledger schema validation:** Hook checks format before writing
- **Session type enum:** `KNOWLEDGE | SIMPLE_FIX | BUG_FIX | FEATURE`
- **Reset protocol:** Clear active sections before workflow start (preserve history in archive)

### 3.5 Context Compaction Issues

**Source:** #48

**Problem:** Context compaction mid-task loses user feedback signals.

**Recommendation:**

- **Conditional compaction:** Only compact when no pending user input
- **Preserve user turns:** Never compact user messages or immediate responses
- **Ledger checkpoint:** Save state before compaction for seamless resume

---

## 4. Ledger & State Management

### 4.1 Work Breakdown & Tracking

**Source:** #27, #47

**Problem:** No dedicated agent for work breakdown; ledger updates inconsistent; no approval indicator for next agent.

**Recommendation:**

- **Work Breakdown Agent:** Takes high-level plan → produces structured task list → updates ledger
- **Ledger template enforcement:** JSON schema or markdown template for consistency
- **Approval flags:** Add `approved: true/false` field in ledger task entries
- **Status transitions:** `PENDING → IN_PROGRESS → REVIEW → APPROVED → COMPLETE`

### 4.2 Infinite Loop Prevention

**Source:** #12

**Problem:** No safeguards against infinite loops.

**Recommendation:**

- **Iteration counter:** Max 10 iterations per loop ID
- **Timeout:** 2-hour wall clock limit
- **Exit condition check:** Every iteration validates exit criteria
- **Manual override:** User can force-exit loop via special command

---

## 5. Memory Management

### 5.1 Memory Storage Confusion

**Source:** #13, #30, #43

**Problem:** Orchestrator tries to write to `/memories/repo/` (Copilot internal, not in repo); learnings written to ledger instead of memory; unclear what happens when repo moves to another machine.

**Impact:** Learnings not portable; memory fragmented across ledger/memory/instructions.

**Recommendation:**

- **Disable `/memories/repo/`:** Enforce `.github/solar-system/` for all repo-specific state
- **Learning destination:** `.github/solar-system/.learnings/LEARNINGS.md` (in repo, version controlled)
- **Memory hierarchy:**
  - Ephemeral (session): Ledger active sections
  - Persistent (repo): `.github/solar-system/.learnings/`
  - Cross-repo (user): `/memories/` (user preferences only)
- **Migration guide:** Document memory → solar-system migration path

---

## 6. Agent Specialization & Tiers

### 6.1 Agent Role Boundaries Blur

**Source:** #14, #25, #37, #39, #45

**Problem:** Curator doesn't ask for design/template; implementor does extra work (test coverage checks, dependency installs); implementor reads too many files; no clear delegation order.

**Impact:** Role confusion, wasted context, redundant work, cost inflation.

**Recommendation:**

**Define strict agent tiers:**

| Tier            | Role              | MUST DO                                      | MUST NOT DO                                   |
| --------------- | ----------------- | -------------------------------------------- | --------------------------------------------- |
| **Collector**   | Data gathering    | Read files, grep, semantic search, summarize | Code, analyze, make decisions                 |
| **Planner**     | Design & planning | Design, plan, review reports                 | Broad reading, code, write excessive docs     |
| **Implementor** | Code execution    | Code, test, commit                           | Think/analyze, broad research, read >10 files |
| **Reviewer**    | Quality gates     | Review, audit, suggest fixes                 | Implement fixes directly                      |

**Delegation order:** User → Orchestrator → Collector → Planner → Implementor → Reviewer → Orchestrator

**Curator rule:** ALWAYS ask for design/template when uncertain (mirror implementor's escalation pattern)

**Implementor input contract:** Receives design doc + verification artifact; if missing data, delegate to Collector NOT broad search

### 6.2 Collector Agent Missing

**Source:** #37, #22, #45

**Problem:** No dedicated data gathering agent; orchestrator and implementor do broad searches.

**Recommendation:**

- **New agent:** Data Collector Specialist
- **Invocation rule:** ALWAYS invoke collector before planner
- **Output format:** Structured summary (not raw file dumps)
- **Verification artifact integration:** Collector populates artifact, implementor consumes it

---

## 7. Documentation Quality

### 7.1 Documentation Process Gaps

**Source:** #14, #17, #19, #20, #23, #33, #34, #41

**Problems:**

- Curator doesn't escalate when design unclear
- Unclear when/which docs to update (instructions vs workflow vs memory)
- No dedicated docs reviewer (overloads other reviewers)
- Implementor creates excessive/unrealistic docs
- Curator produces format errors
- Wrong tech stack in design docs
- Everything dumped into main copilot-instructions
- Template compliance weak
- Wrong file format/directory from poor design

**Impact:** Documentation overhead without accuracy; review bottleneck; template drift; duplicate/misplaced guidance.

**Recommendations:**

**7.1.1 Dedicated Docs Reviewer**

- New role or expand existing reviewer scope
- Pre-approval format check (schema validation)
- Tech stack verification against `.github/instructions/`

**7.1.2 Minimal Docs Policy**

- Prefer accuracy over quantity
- Realistic acceptance criteria only
- No speculative implementation details

**7.1.3 Documentation Update Decision Tree**

- **Instructions:** Tech stack, conventions, security rules
- **Workflows:** Process flows, agent routing, handoff patterns
- **Memory/Learnings:** Reusable patterns, mistakes, edge cases
- **Ledger:** Active task state only (not permanent)

**7.1.4 Template Enforcement**

- ALWAYS check template first (create/update/review)
- Schema validation hook for doc commits
- Curator asks "which template?" if unsure

**7.1.5 Split Instructions**

- Stop monolithic `copilot-instructions.md`
- Specific `.instructions.md` per domain (frontend/backend/security/etc.)
- Main file only for orchestration rules

### 7.2 Wrong Tech Stack in Docs

**Source:** #24, #44

**Problem:** Design docs use wrong tech stack; UI designs inconsistent with current system.

**Recommendation:**

- **Design phase verification:** Planner reads `.github/instructions/` before design
- **UI design checklist:** Screenshots of current UI required before new UI design
- **Tech stack anchor:** Single source of truth in instructions (frontend/backend files)

---

## 8. Code Implementation Issues

### 8.1 Implementor Scope Creep

**Source:** #18, #25

**Problem:** Implementor does work not in scope (test coverage checks, dependency installs); high-level agents produce too many/complex change requests without control.

**Recommendation:**

- **Strict scope enforcement:** Implementor only implements what's in handoff template
- **Escalation rule:** If scope unclear or extra work needed, STOP and delegate back to planner/orchestrator
- **Change request limits:** Max 5 file changes per task; max 50 lines per file; flag for review if exceeded (start with logging, add hard limits later)

### 8.2 Adaptation Gap (Cross-Domain Consistency)

**Source:** #40

**Problem:** Features requiring frontend + backend changes go off-rail when designs don't match (e.g., API contract mismatch).

**Recommendation:**

- **Unified design phase:** Planner produces single design covering all domains
- **API contract first:** Define API spec before frontend/backend implementation
- **Cross-domain review:** Review auditor checks frontend-backend alignment
- **Design template section:** "Cross-Domain Dependencies" (API contracts, shared types, data flow)

### 8.3 Implementation Research Overload

**Source:** #45

**Problem:** Implementor reads too many files, pollutes context, causes hallucinations.

**Recommendation:**

- **Max read limit:** 10 files per task
- **Verification artifact pattern:** Collector prepares data, implementor consumes (already working well)
- **Input contract:** Design doc + verification artifact = sufficient; if not, escalate NOT search

---

## 9. User Interaction & Approval

### 9.1 Missing Interaction Tools

**Source:** #5, #7, #47

**Problem:** Orchestrator doesn't ask when uncertain; no use of `vscode/askQuestion` for intent clarification; no approval indicator for next agent.

**Recommendation:**

- **askQuestion integration:** Use for workflow selection, scope clarification, ambiguity resolution
- **Approval workflow:** User confirms design → sets `approved: true` in ledger → implementor proceeds
- **Explicit gates:** "Waiting for user approval" status in ledger

---

## 10. Agent Communication & Handoffs

### 10.1 Handoff Patterns

**Source:** #25, #26, #32, #38

**What's Working:** Deliverable template handoffs work well ✓

**Problems:** Agents don't always delegate back when uncertain; subagent steering in loop unclear.

**Recommendation:**

- **Preserve deliverable template pattern:** Use across all agent transitions
- **Escalation rule:** When uncertain, delegate BACK (implementor → planner, planner → orchestrator)
- **Subagent loop pattern:** Subagent writes progress to ledger; orchestrator reads ledger to resume
- **Communication channels:**
  - Forward: Handoff template
  - Lateral: Ledger read
  - Backward: Escalation handoff

---

## 11. Logging & Observability

### 11.1 Missing Logs

**Source:** #16, #28

**Problem:** Hooks not writing to logs; some v4 features not working (log/learning/protocol).

**Recommendation:**

- **Hook logging:** All hooks write to `.github/solar-system/logs/<hook-name>.log`
- **Feature audit:** Test log/learning/protocol features; fix or remove broken ones
- **Log rotation:** Daily logs, keep last 7 days
- **Observability dashboard:** Summary view of loop iterations, agent invocations, errors

---

## 12. Output Quality & Model Selection

### 12.1 Agent Verbosity

**Source:** #8, #35

**Problem:** Agents explain too much; output bloated.

**Recommendation:**

- **Concise mode:** Add to all agent instructions: "Output format: concise, no explanations unless requested"
- **Model selection:** Use Haiku for fast agents (implementor, collector); compact frequently
- **Output templates:** Structured formats reduce prose

### 12.2 Model Inheritance Issue

**Source:** #36

**Problem:** Invoked agent seems capped at invoker's model (needs verification).

**Impact:** High-reasoning tasks invoked by low-tier agent may fail.

**Recommendation:**

- **Verify behavior:** Test if subagent inherits invoker model or uses own frontmatter model
- **If confirmed:** Document in troubleshooting; avoid invoking high-tier agents from low-tier agents
- **Workaround:** Orchestrator invokes high-tier directly, not via low-tier agent

---

## 13. What's Working Well

### 13.1 Successes to Preserve

**Source:** #21, #31, #32, #42

✅ **Pipeline recognition** — Feature pipeline routing effective  
✅ **Verification artifacts** — Good data central pattern for agents  
✅ **Deliverable templates** — Smooth handoffs between agents  
✅ **Pipeline stage notifications** — Clear visibility into progress

**Action:** Document these patterns as golden paths; extract into reusable templates.

---

## 14. Technical Bugs

### 14.1 Terminal Cleanup

**Source:** #50

**Problem:** Background terminals don't exit cleanly.

**Recommendation:**

- **Hook fix:** `stop.cjs` should kill all spawned terminals
- **Process tracking:** Maintain PID list in ledger
- **Timeout kill:** Force-kill after 5s grace period

---

<a id="v4-features-status-table"></a>

# Part 2: v4 Features Status Table

**Purpose:** Track all 31 v4 implementation plan features with verification status and feedback impact.

**Legend:**

- **Status:** ✅ Working | ⚠️ Partial/Not Visible | ❌ Broken
- **Obsolete After Feedback:**
  - 🔄 **REPLACE** — Feedback recommendation overwrites this feature
  - ✅ **FIX** — Feedback repairs/clarifies this feature
  - ➕ **EXTEND** — Feedback adds to this feature
  - 🛡️ **PRESERVE** — Feature works, feedback preserves it
  - ⚡ **DEFER** — Feature blocked or deferred

---

## Phase 1: Solar-System Foundation (1.1-1.6)

| Feature | Description                              | Status         | Obsolete?   | Related Feedback                                    |
| ------- | ---------------------------------------- | -------------- | ----------- | --------------------------------------------------- |
| 1.1     | `.github/solar-system/` folder structure | ⚠️ Partial     | ✅ FIX      | §1.1 (fix setup), §5.1 (clarify learnings location) |
| 1.2     | LEARNINGS/ERRORS/FEATURE_REQUESTS.md     | ❌ Not working | ✅ FIX      | §5.1 Memory Consolidation (P0.4)                    |
| 1.3     | `session-start.cjs` hook                 | ⚠️ Not visible | ✅ FIX      | §11.1 Hook Logging (P2.12)                          |
| 1.4     | `user-prompt-submit.cjs` hook            | ⚠️ Not visible | ✅ FIX      | §11.1 Hook Logging (P2.12)                          |
| 1.5     | `post-tool-use.cjs` ERRORS.md append     | ⚠️ Not visible | ✅ FIX      | §11.1 Hook Logging (P2.12)                          |
| 1.6     | `CONTEXT-EFFICIENCY.md` guidelines       | ⚠️ Not visible | 🛡️ PRESERVE | None — guideline doc                                |

**Phase 1 Summary:** Foundation exists but learning capture broken. Feedback fixes storage location confusion and adds hook logging.

---

## Phase 2: Trust Enforcement (2.1-2.7)

| Feature | Description                                  | Status         | Obsolete?   | Related Feedback                |
| ------- | -------------------------------------------- | -------------- | ----------- | ------------------------------- |
| 2.1     | Watch Mode inquiry gate (`pre-tool-use.cjs`) | ❌ Not working | ✅ FIX      | §3.2 (P0.5 Inquiry Gate Repair) |
| 2.2     | Inquiry-first protocol doc                   | ⚠️ Not visible | ✅ FIX      | §3.2 (P0.5 Inquiry Gate Repair) |
| 2.3     | Ledger inquiry gate section                  | ❌ Not working | ✅ FIX      | §3.2 (P0.5 Inquiry Gate Repair) |
| 2.4     | Designer/implementor handoff schemas         | ✅ Working     | 🛡️ PRESERVE | §13.1 (What's Working)          |
| 2.5     | Schema enforcement in agents                 | ✅ Working     | 🛡️ PRESERVE | §13.1 (What's Working)          |
| 2.6     | Watch Mode adversarial skeleton manifest     | ⚠️ Not visible | 🛡️ PRESERVE | None — safety mechanism         |
| 2.7     | Watch Mode pre-checks                        | ⚠️ Not visible | 🛡️ PRESERVE | None — safety mechanism         |

**Phase 2 Summary:** Inquiry gate completely bypassed (highest-priority safety failure). Handoff schemas work well. Feedback repairs inquiry gate enforcement.

---

## Phase 3: Inter-Agent Communication (3.1-3.8)

| Feature | Description                           | Status         | Obsolete?   | Related Feedback                                                       |
| ------- | ------------------------------------- | -------------- | ----------- | ---------------------------------------------------------------------- |
| 3.1     | Subagent accept hook (`subagent.cjs`) | ⚠️ Not visible | 🛡️ PRESERVE | §10.1 (handoff patterns preserved)                                     |
| 3.2     | Subagent escalate hook                | ⚠️ Not visible | 🛡️ PRESERVE | §10.1 (escalation rule added)                                          |
| 3.3     | Handoff type schemas (JSON)           | ✅ Working     | 🛡️ PRESERVE | §13.1 (What's Working)                                                 |
| 3.4     | Lifecycle protocol docs               | ⚠️ Not visible | 🛡️ PRESERVE | None — documented patterns                                             |
| 3.5     | Router pipeline integration           | ⚠️ Not visible | 🛡️ PRESERVE | None — routing logic                                                   |
| 3.6     | Ledger handoff sections               | ✅ Working     | ➕ EXTEND   | §3.3 (P0.3 adds Active Loops section)                                  |
| 3.7     | Router pipeline (RAG, JIT)            | ✅ Working     | 🔄 REPLACE  | §2.1 (P1.5 Workflow Architecture Migration)                            |
| 3.8     | Governor skip logic & handoff payload | ✅ Working     | 🔄 REPLACE  | §3.1 (P0.2 Orchestrator Delegation), §6.1 (P0.1 Agent Tier Boundaries) |

**Phase 3 Summary:** Ledger/Router/Governor core working. Feedback proposes MAJOR architectural change (workflow replacement of pipelines) and strict agent tier boundaries. High conflict risk if implemented.

---

## Phase 4: Context Efficiency (4.1-4.6)

| Feature | Description                 | Status              | Obsolete?   | Related Feedback                      |
| ------- | --------------------------- | ------------------- | ----------- | ------------------------------------- |
| 4.1     | Effort simulation guide     | ✅ Working          | ➕ EXTEND   | §4.1 (P1.7 Work Breakdown Agent)      |
| 4.2     | Pipeline JIT loading        | ⚠️ Not visible      | 🛡️ PRESERVE | None — loading mechanism              |
| 4.3     | Governor pipeline selection | ⚠️ Not visible      | 🔄 REPLACE  | §2.1 (P1.5 Workflow Architecture)     |
| 4.4     | `pre-compact.cjs` hook      | ❌ Platform blocked | ⚡ DEFER    | §3.5 (P2.11 polling-based workaround) |
| 4.5     | Governor ledger compaction  | ⚠️ Not visible      | 🛡️ PRESERVE | §3.5 (conditional compaction)         |
| 4.6     | Context config fields       | ❌ Not used         | 🛡️ PRESERVE | None — config exists                  |

**Phase 4 Summary:** Effort guide works. Pre-compact hook blocked by VS Code platform limitation. Pipeline JIT loading invisible but likely working. Feedback adds Work Breakdown Agent on top of effort guide.

---

## Phase 5: Gap Closure (5.1-5.14)

| Feature | Description                            | Status          | Obsolete?   | Related Feedback                                           |
| ------- | -------------------------------------- | --------------- | ----------- | ---------------------------------------------------------- |
| 5.1     | Greedy capture in bootstrap            | ⚠️ Partial      | 🛡️ PRESERVE | None — setup improvement                                   |
| 5.2     | Setup scan review nudge                | ✅ Working      | 🛡️ PRESERVE | None — setup improvement                                   |
| 5.3     | AGENTS.md baseline redesign            | ✅ Working      | 🔄 REPLACE  | §2.1 (P1.5 workflow migration affects AGENTS.md structure) |
| 5.4     | JIT pipeline files                     | ✅ Working      | 🔄 REPLACE  | §2.1 (P1.5 replaces pipeline files with workflow files)    |
| 5.5     | Governor JIT pipeline loading          | ✅ Working      | 🔄 REPLACE  | §2.1 (P1.5 loads workflow files instead)                   |
| 5.6     | Project-unbiased agents                | ✅ Working      | 🛡️ PRESERVE | §13.1 (success pattern)                                    |
| 5.7     | Prompt authoring guide update          | ⚠️ Not measured | 🛡️ PRESERVE | None — guide update                                        |
| 5.8     | Output position contract (implementor) | ✅ Working      | 🛡️ PRESERVE | §13.1 (implementor read-before-write works)                |
| 5.9     | Output contract enforcement (planner)  | ⚠️ Partial      | ✅ FIX      | §7.1, §7.2 (P1.6 Docs Reviewer fixes planner errors)       |
| 5.10    | Format safety in solar.instructions    | ⚠️ Not visible  | 🛡️ PRESERVE | None — instruction text                                    |
| 5.11    | Session log creation                   | ❌ Not working  | ✅ FIX      | §11.1 (P1.9 Session Logging Fix)                           |
| 5.12    | Session log event appending            | ❌ Not working  | ✅ FIX      | §11.1 (P1.9 Session Logging Fix)                           |
| 5.13    | Session log termination                | ❌ Not working  | ✅ FIX      | §11.1 (P1.9 Session Logging Fix)                           |
| 5.14    | Log sources reference                  | ❌ Not working  | ✅ FIX      | §11.1 (P1.9 Session Logging Fix)                           |

**Phase 5 Summary:** Setup improvements (5.1-5.6, 5.8) work well. Session logging (5.11-5.14) completely broken. Pipeline-related features (5.3-5.5) work but will be obsolete if workflow migration implemented. Feedback fixes session logging and planner output contract.

---

## Summary: Working vs Broken vs Obsolete

### ✅ Working (9 features, 29%)

- 2.4-2.5: Handoff schemas
- 3.3, 3.6-3.8: Handoffs, ledger sections, Router pipeline, Governor logic
- 4.1: Effort simulation guide
- 5.2-5.6, 5.8: Setup improvements, unbiased agents, implementor output contract

**Feedback Impact:** Preserved (5 features), Extended (1 feature), Replaced if workflow migration (3 features)

### ⚠️ Partial / Not Visible (12 features, 39%)

- 1.1, 1.3-1.6: Phase 1 foundation (files exist but hooks not visible)
- 2.2, 2.6-2.7: Inquiry protocol docs, Watch Mode pre-checks
- 3.1-3.2, 3.4-3.5: Subagent hooks, lifecycle protocols, Router integration
- 4.2, 4.5: Pipeline JIT loading, governor compaction
- 5.1, 5.7, 5.9-5.10: Greedy capture, prompt guide, planner contract, format safety

**Feedback Impact:** Fixed (4 features), Preserved (8 features)

### ❌ Broken / Not Working (10 features, 32%)

- 1.2: LEARNINGS/ERRORS/FEATURE_REQUESTS.md not populated
- 2.1, 2.3: Inquiry gate bypassed
- 4.4: Pre-compact hook blocked by platform
- 4.6: Context config fields not used
- 5.11-5.14: Session logging non-functional

**Feedback Impact:** Fixed (8 features), Deferred (1 feature), Preserved (1 feature)

### 🔄 High-Risk Replacements (if feedback implemented)

**P1.5 Workflow Architecture Migration (§2.1):**

- Replaces: 3.7 (Router pipeline), 5.3 (AGENTS.md), 5.4 (pipeline files), 5.5 (JIT loading)
- Risk: EXTREME — breaks entire pipeline system
- Recommendation: **DEFER to v6**

**P0.1 Agent Tier Boundaries (§6.1):**

- Replaces: 3.8 (Governor delegation logic), all 16 agent.md files
- Risk: MODERATE — requires rewriting all agents
- Recommendation: **Phased rollout** (add tier frontmatter → create Collector → enforce)

**P0.2 Orchestrator Delegation (§3.1):**

- Replaces: 3.8 (Governor file-reading capability)
- Risk: HIGH — may break Router pipeline task classification
- Recommendation: **Hybrid approach** (allow 3-file reads for classification only)

---

## Priority Recommendations Based on Feature Status

### v5.0 (Safe Changes — Fixes Only)

**P0 Fixes (No Architectural Risk):**

1. ✅ Fix inquiry gate (2.1, 2.3) — §3.2 (P0.5)
2. ✅ Fix learning capture (1.2) — §5.1 (P0.4)
3. ✅ Fix session logging (5.11-5.14) — §11.1 (P1.9)
4. ✅ Fix hook logging (1.3-1.5) — §11.1 (P2.12)
5. ✅ Fix planner output contract (5.9) — §7.1, §7.2 (P1.6)

**P1 Additions (Pure New Features):** 6. 🆕 Add Docs Reviewer agent — §7.1.1 (P1.6) 7. 🆕 Add Work Breakdown agent — §4.1 (P1.7) 8. ➕ Add Loop Invocation mechanism — §3.3 (P0.3)

### v5.1 (Staged Rollout — Agent Tiers)

9. 🔄 Add tier: frontmatter to agents (non-breaking) — §6.1 (P0.1 Phase 1)
10. 🆕 Create Data Collector Specialist — §6.1 (P0.1 Phase 2)
11. 🔄 Hybrid orchestrator delegation rules — §3.1 (P0.2 compromise)

### v6.0 (Major Architecture Change)

12. 🔄 Workflow Architecture migration (replace pipelines) — §2.1 (P1.5)

---

<a id="draft-mapping-table"></a>

# Part 3: Draft Mapping Table

**Purpose:** Track 51 original draft feedback items to organized sections in Part 1.  
**Status:** Temporary tracking artifact — will be removed after v5 implementation complete.

---

| Draft # | Category         | Main Point                           | Organized Section |
| ------- | ---------------- | ------------------------------------ | ----------------- |
| 1       | Setup            | Template merge/rename fail           | 1.1               |
| 2       | Setup            | Duplicate solar folders              | 1.1               |
| 3       | Architecture     | Workflow location unclear            | 2.1               |
| 4       | Architecture     | Replace pipelines with workflows     | 2.1               |
| 5       | User Interaction | Ask before proceeding                | 3.2, 9.1          |
| 6       | User Interaction | Hint user on gaps                    | 3.2               |
| 7       | User Interaction | Use askQuestion                      | 9.1               |
| 8       | Output           | Use Haiku, compact frequently        | 12.1              |
| 9       | Orchestrator     | No loop invocation mechanism         | 3.3               |
| 10      | Orchestrator     | Ralph-loop trigger undefined         | 3.3               |
| 11      | Ledger           | Wrong session type format            | 3.4               |
| 12      | Ledger           | No infinite loop prevention          | 4.2               |
| 13      | Memory           | /memory/repo usage unclear           | 5.1               |
| 14      | Documentation    | Curator doesn't ask for design       | 6.1, 7.1          |
| 15      | Ledger           | Reset ledger before workflow         | 3.4               |
| 16      | Logging          | Hooks not writing logs               | 11.1              |
| 17      | Documentation    | Unclear when/which docs to update    | 7.1.3             |
| 18      | Implementation   | No control on change complexity      | 8.1               |
| 19      | Documentation    | Need dedicated docs reviewer         | 7.1.1             |
| 20      | Documentation    | Minimize docs, prefer accuracy       | 7.1.2             |
| 21      | Architecture     | Pipeline recognition works ✓         | 2.1, 13.1         |
| 22      | Orchestrator     | Unnecessary file reading             | 3.1               |
| 23      | Documentation    | Curator format errors                | 7.1.4             |
| 24      | Documentation    | Wrong tech stack in docs             | 7.2               |
| 25      | Implementation   | Implementor scope creep              | 6.1, 8.1          |
| 26      | Communication    | Subagent steering in loop            | 10.1              |
| 27      | Ledger           | Need work breakdown agent            | 4.1               |
| 28      | Logging          | v4 features broken                   | 11.1              |
| 29      | Setup            | [FILL IN] not replaced               | 1.1               |
| 30      | Memory           | /memories/repo/ portability issue    | 5.1               |
| 31      | Success          | Verification artifacts work ✓        | 13.1              |
| 32      | Success          | Deliverable templates work ✓         | 13.1, 10.1        |
| 33      | Documentation    | Split instructions                   | 7.1.5             |
| 34      | Documentation    | Enforce template compliance          | 7.1.4             |
| 35      | Output           | Agents too verbose                   | 12.1              |
| 36      | Output           | Model inheritance issue              | 12.2              |
| 37      | Agent Tiers      | Delegate to collector first          | 6.1, 6.2          |
| 38      | Orchestrator     | Programmatic workflow init           | 3.1               |
| 39      | Agent Tiers      | Define agent tier boundaries         | 6.1               |
| 40      | Implementation   | Cross-domain adaptation gap          | 8.2               |
| 41      | Documentation    | Wrong file format from bad design    | 7.1, 7.2          |
| 42      | Architecture     | Pipeline notifications good, migrate | 2.1, 13.1         |
| 43      | Memory           | Learnings to ledger not memory       | 5.1               |
| 44      | Implementation   | UI design inconsistent               | 7.2               |
| 45      | Implementation   | Implementor research overload        | 6.1, 8.3          |
| 46      | Orchestrator     | Upgrade model once delegating        | 3.1               |
| 47      | User Interaction | Need approval indicator              | 4.1, 9.1          |
| 48      | Orchestrator     | Conditional context compaction       | 3.5               |
| 49      | Orchestrator     | Check user feedback actively         | 3.2               |
| 50      | Technical        | Terminal cleanup issue               | 14.1              |
| 51      | Orchestrator     | Track loss in extensive cycles       | 3.1               |

---

## Priority Recommendations

### P0 (Critical — Blocks v5)

1. **Agent tier boundaries** — Define strict collector/planner/implementor/reviewer roles (§6.1)
2. **Orchestrator delegation** — Stop file reading, minimize tool use (§3.1)
3. **Loop invocation mechanism** — Flag-based loop mode with ledger tracking (§3.3)
4. **Memory consolidation** — Disable `/memories/repo/`, enforce solar-system (§5.1)

### P1 (High — Quality Impact)

5. **Workflow architecture** — Migrate from pipelines to composable workflows (§2.1)
6. **Dedicated docs reviewer** — Prevent format errors and tech stack mismatches (§7.1.1, §7.2)
7. **Work breakdown agent** — Structured task decomposition with ledger template (§4.1)
8. **Collector agent** — Data gathering before planning (§6.2)

### P2 (Medium — UX Improvement)

9. **askQuestion integration** — Clarify intent, confirm workflow (§9.1)
10. **Approval workflow** — User confirmation gates in ledger (§9.1)
11. **Infinite loop prevention** — Iteration limits, timeouts (§4.2)
12. **Hook logging** — Observability for debugging (§11.1)

### P3 (Low — Polish)

13. **Output verbosity** — Concise mode enforcement (§12.1)
14. **Template merge installer** — Fix setup automation (§1.1)
15. **Terminal cleanup** — Background process management (§14.1)
16. **Model inheritance investigation** — Verify and document behavior (§12.2)

---

### v4 Feature Priority Additions (Based on Part 2 Feature Verification)

**Add to P0 (Critical):**

- **Inquiry gate repair** — Phase 2 features 2.1-2.3 completely bypassed; safety mechanism non-functional (see Part 2)
- **Learning capture activation** — Phase 1 features 1.1-1.6 not writing to LEARNINGS.md/ERRORS.md; cross-session knowledge lost (see Part 2)

**Add to P1 (High):**

- **Session logging implementation** — Phase 5 features 5.11-5.14 broken; `.github/solar-system/logs/` not created; debugging impossible (see Part 2)

**Move to P2 (Platform-Blocked):**

- **Pre-compact hook** — Feature 4.4 blocked by VS Code limitation; requires polling-based workaround instead of hook (see Part 2)

**Note on Planner Output Contract (5.8-5.9):**
Implementor enforces read-before-write correctly, but planner still outputs wrong file locations. This is §7.2 (Wrong Tech Stack in Docs) already in P1 — design phase verification needed.

---

## Testing Methodology Note

This feedback was gathered during a complete epic implementation cycle (Epic 16: multi-story feature with frontend/backend coordination, API contracts, UI updates, and cross-cutting concerns). The orchestrator managed 8+ agents across 15+ tasks over 72 hours of development time, exposing both workflow successes and breakdown patterns under realistic load.

**Feature Verification:** Each v4 implementation plan feature (31 total across 5 phases) was verified for visibility and functionality during the Epic 16 cycle. Results: 29% working, 39% partial/not visible, 32% broken. Full verification findings in Part 2.
