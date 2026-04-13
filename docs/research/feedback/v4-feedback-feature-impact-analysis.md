# v4 Feedback Feature Impact Analysis

**Purpose:** Identify which feedback recommendations resolve, overwrite, or conflict with original v4 implementation plan features.

**Source Documents:**

- v4 Implementation Plan: `docs/work-logs/v4-implementation-plan.md`
- v4 Feedback: `docs/research/feedback/SOLAR-Ralph-v4-feedback.md`
- Feature Verification: §15 of v4 Feedback

**Date:** April 10, 2026

---

## Impact Categories

- **✅ FIXES** — Repairs broken/non-functional v4 feature
- **🔄 OVERWRITES** — Replaces v4 feature with different approach
- **⚠️ CONFLICTS** — Creates tension/incompatibility with v4 feature
- **➕ EXTENDS** — Adds to v4 feature without replacing
- **🆕 NEW** — Creates capability v4 doesn't have

---

## P0 (Critical) Recommendations

### 1. Agent Tier Boundaries (§6.1)

**Type:** 🔄 OVERWRITES + 🆕 NEW

**v4 Features Affected:**

- Phase 3 (3.1-3.8): Inter-Agent Communication Infrastructure
- Existing agent files: All 16 agents in `.github/agents/`

**Impact:**

- **OVERWRITES:** Current agent delegation pattern (orchestrator → any specialist)
- **NEW PATTERN:** Enforces strict delegation order: Orchestrator → Collector → Planner → Implementor → Reviewer
- **NEW AGENT:** Data Collector Specialist (doesn't exist in v4)

**v4 Feature Map:**
| v4 Feature | Status | New Behavior |
|------------|--------|--------------|
| 3.8 Governor handoffs | Partial | Must delegate to Collector FIRST before any planner |
| All agent.md files | Working | Add tier: frontmatter field + role constraints |

**Conflict Risk:** ⚠️ MODERATE

- Current agents have overlapping capabilities (implementor reads files, planner can code)
- Strict tier boundaries prevent current "smart delegation" where orchestrator skips to implementor for simple fixes
- Requires rewriting all 16 agent instruction bodies

**Resolution Strategy:**

- Phase 1: Add tier: frontmatter to all agents (non-breaking)
- Phase 2: Enforce tier rules in orchestrator (breaking: changes delegation logic)
- Phase 3: Create Collector agent, update governor to always invoke collector before planner

---

### 2. Orchestrator Delegation (§3.1)

**Type:** 🔄 OVERWRITES

**v4 Features Affected:**

- Phase 3 (3.6-3.8): Ledger handoff sections, Router pipeline, Governor logic
- Phase 4 (4.5): Governor ledger compaction

**Impact:**

- **OVERWRITES:** Orchestrator's current "read files to understand task" behavior
- **NEW CONSTRAINT:** Orchestrator ONLY delegates, reads ledger, routes; NO file reading, NO grep/semantic search
- **DEPENDENCY:** Requires Collector agent (Rec #1) to gather context for orchestrator

**v4 Feature Map:**
| v4 Feature | Status | New Behavior |
|------------|--------|--------------|
| 3.6 Ledger handoff sections | ✅ Working | PRESERVED — orchestrator reads ledger for results |
| 3.7 Router pipeline | ✅ Working | PRESERVED — router still classifies signals |
| 3.8 Governor skip logic | ✅ Working | MODIFIED — skip logic preserved, but add "invoke collector first" rule |
| 4.5 Governor compaction | Not visible | PRESERVED — compaction trigger logic unchanged |

**Conflict Risk:** ⚠️ HIGH

- Current governor reads 1-3 files before delegating (Phase 3 tiered context gate)
- This recommendation REMOVES that capability entirely
- Governor may not have enough context to classify task → route to wrong pipeline

**Resolution Strategy:**

- **Option A (Strict):** Remove all file-reading tools from governor; force collector invocation on every task
- **Option B (Hybrid):** Allow governor to read up to 3 files for classification ONLY; all other context gathering via collector
- **Recommended:** Option B — preserves Router pipeline effectiveness while minimizing orchestrator context load

---

### 3. Loop Invocation Mechanism (§3.3)

**Type:** 🆕 NEW + ➕ EXTENDS

**v4 Features Affected:**

- None directly — v4 has no loop invocation mechanism

**Impact:**

- **NEW:** Workflow metadata `loop: true` flag
- **NEW:** Ledger section `## Active Loops`
- **EXTENDS:** Phase 3 (3.6) ledger template with loop tracking fields

**v4 Feature Map:**
| v4 Feature | Status | New Behavior |
|------------|--------|--------------|
| 3.6 Ledger handoff sections | ✅ Working | ADD `## Active Loops` section (non-breaking) |
| 3.8 Governor skip logic | ✅ Working | ADD loop mode detection logic (non-breaking) |

**Conflict Risk:** ✅ NONE — Pure addition, no overwrites

**Resolution Strategy:**

- Add loop metadata to workflow files in `solar-system/pipelines/`
- Update `.ai_ledger.template.md` with `## Active Loops` section
- Add loop detection logic to governor's pipeline selection block

---

### 4. Memory Consolidation (§5.1)

**Type:** 🔄 OVERWRITES

**v4 Features Affected:**

- Phase 1 (1.2): Learning capture files in `.github/solar-system/.learnings/`
- Phase 1 (1.3): `session-start.cjs` injects LEARNINGS.md summary
- All references to `/memories/repo/` in agent instructions

**Impact:**

- **OVERWRITES:** Phase 1's design of learning storage location (already in `solar-system/.learnings/`)
- **CLARIFIES:** Disables `/memories/repo/` usage (Copilot internal, outside repo)
- **BUG FIX:** Aligns with v4 Phase 1 intent but contradicts current agent behavior

**v4 Feature Map:**
| v4 Feature | Status | New Behavior |
|------------|--------|--------------|
| 1.2 LEARNINGS/ERRORS/FEATURE_REQUESTS.md | ❌ Not working | FIX — enforce `solar-system/.learnings/` as exclusive location |
| 1.3 session-start.cjs injection | Not visible | VERIFY — ensure hook reads from correct location |
| All agent.md files | Working | REMOVE references to `/memories/repo/`, add enforcement to write to `solar-system/.learnings/` only |

**Conflict Risk:** ✅ LOW — This FIXES broken v4 behavior rather than conflicting

**Resolution Strategy:**

- Audit all agent.md files for `/memories/repo/` references → remove
- Add explicit instruction: "NEVER write to `/memories/repo/`; use `.github/solar-system/.learnings/` only"
- Verify `session-start.cjs` reads from `solar-system/.learnings/LEARNINGS.md`

---

### 5. Inquiry Gate Repair (§15 + §2.1-2.3)

**Type:** ✅ FIXES

**v4 Features Affected:**

- Phase 2 (2.1-2.3): Watch Mode inquiry gate, inquiry-first protocol, ledger inquiry gate section

**Impact:**

- **FIXES:** Broken Phase 2 features — inquiry gate completely bypassed during Epic 16 test
- **ROOT CAUSE:** Likely missing enforcement in governor or pre-tool-use.cjs

**v4 Feature Map:**
| v4 Feature | Status | Fix Required |
|------------|--------|--------------|
| 2.1 Watch Mode inquiry gate | ❌ Not working | Verify `pre-tool-use.cjs` has correct tool patterns; test permissionDecision: "ask" output |
| 2.2 Inquiry-first protocol | ❌ Not working | Verify `solar-system/protocols/inquiry-first.md` exists; check if governor reads it |
| 2.3 Ledger inquiry gate | ❌ Not working | Verify `## Inquiry Gate` section in ledger template; add governor enforcement before delegation |

**Conflict Risk:** ✅ NONE — Pure repair of intended v4 functionality

**Resolution Strategy:**

1. **Phase 2.1 Verification:** Test `pre-tool-use.cjs` with exact tool call names used during Epic 16 → confirm hook fires
2. **Phase 2.2 Verification:** Check if governor instructions reference `inquiry-first.md` → add if missing
3. **Phase 2.3 Enforcement:** Add explicit check in governor: "Before delegating to ANY implementation agent, verify Inquiry Gate section in ledger has all checkboxes checked. If not, STOP and return to Design Planning Architect."

---

### 6. Learning Capture Activation (§15 + §1.1-1.6)

**Type:** ✅ FIXES

**v4 Features Affected:**

- Phase 1 (1.1-1.6): All solar-system foundation features

**Impact:**

- **FIXES:** Broken Phase 1 features — no observable output during Epic 16 test
- **ROOT CAUSE:** Hooks exist but not writing to learning files

**v4 Feature Map:**
| v4 Feature | Status | Fix Required |
|------------|--------|--------------|
| 1.3 session-start.cjs | Not visible | Verify hook fires; add logging to confirm execution |
| 1.4 user-prompt-submit.cjs | Not visible | Verify learning-reminder removal complete; test ledger-state checks |
| 1.5 post-tool-use.cjs ERRORS.md | Not visible | Verify hook writes to ERRORS.md on tool failure; test with deliberate failure |
| 1.2 Learning files | ❌ Not working | Check file permissions; verify hooks have correct paths |

**Conflict Risk:** ✅ NONE — Pure repair of intended v4 functionality

**Resolution Strategy:**

1. **Hook Diagnostics:** Add debug logging to all Phase 1 hooks → confirm they fire
2. **Path Verification:** Verify all hooks use absolute paths to `solar-system/.learnings/`
3. **Write Test:** Manually trigger each hook condition → verify file writes occur
4. **Root Cause:** Likely VS Code hook execution context issue or silent failure

---

## P1 (High) Recommendations

### 5. Workflow Architecture Migration (§2.1)

**Type:** 🔄 OVERWRITES (MAJOR)

**v4 Features Affected:**

- **ALL Phase 3 pipelines:** Router (3.7), knowledge, simple-fix, bug-fix, feature
- Phase 5 (5.3-5.5): AGENTS.md baseline redesign, JIT pipeline files
- CHANGELOG v3: 4 canonical pipelines

**Impact:**

- **OVERWRITES:** Entire numbered pipeline architecture (0→1→2→3→4)
- **NEW PATTERN:** Composable workflows with different levels, intertwined
- **REPLACES:** `solar-system/pipelines/pipeline-<N>-<name>.md` files with workflow-based structure

**v4 Feature Map:**
| v4 Feature | Status | New Behavior |
|------------|--------|--------------|
| 3.7 Router pipeline | ✅ Working | REPLACE with workflow router |
| 5.3 AGENTS.md baseline | ✅ Working | PRESERVE (workflows still referenced from AGENTS.md) |
| 5.4 JIT pipeline files | ✅ Working | REPLACE 5 pipeline files with N workflow files |
| 5.5 Governor JIT loading | ✅ Working | MODIFY to load workflow files instead of pipeline files |

**Conflict Risk:** ⚠️ EXTREME — Breaks core v4 architecture

**Breaking Changes:**

- All agent instructions referencing "Pipeline 0-4" must be rewritten
- Governor pipeline selection logic completely replaced
- Ledger `Session-Type` field ENUM changes (no more `BUG_FIX | FEATURE`)
- All documentation/guides referencing pipelines outdated

**Resolution Strategy:**

- **Phase 1 (Design):** Define workflow taxonomy (levels, composition rules)
- **Phase 2 (Parallel):** Build workflow files alongside existing pipelines
- **Phase 3 (Toggle):** Add `solar.config.json` flag: `architecture: "pipeline" | "workflow"`
- **Phase 4 (Migrate):** Switch default to workflow; deprecate pipelines
- **Phase 5 (Remove):** Delete pipeline files after 1 version cycle

**Alternative (Conservative):** Keep pipelines for v5; defer workflow migration to v6

---

### 6. Dedicated Docs Reviewer (§7.1.1)

**Type:** 🆕 NEW

**v4 Features Affected:**

- Existing review agents: Frontend Review Auditor, Backend Review Auditor

**Impact:**

- **NEW AGENT:** Documentation Review Specialist
- **EXTENDS:** Review stage in all pipelines/workflows
- **REDUCES LOAD:** Frontend/Backend reviewers no longer review docs

**v4 Feature Map:**
| v4 Feature | Status | New Behavior |
|------------|--------|--------------|
| Phase 3 pipelines | ✅ Working | ADD docs review stage (optional for Simple Fix) |
| Frontend/Backend Review agents | Working | MODIFY — remove doc review responsibilities |

**Conflict Risk:** ✅ LOW — Pure addition with clear role separation

**Resolution Strategy:**

- Create `documentation-review-specialist.agent.md`
- Add to governor's `agents:` allowlist
- Update Frontend/Backend Review auditor instructions to delegate doc review to specialist

---

### 7. Work Breakdown Agent (§4.1)

**Type:** 🆕 NEW + ➕ EXTENDS

**v4 Features Affected:**

- Phase 3 (3.6): Ledger handoff sections
- Phase 4 (4.1): Effort simulation guide

**Impact:**

- **NEW AGENT:** Work Breakdown Specialist
- **NEW LEDGER SECTION:** `## Task Breakdown` with JSON/markdown template
- **EXTENDS:** Replaces ad-hoc governor task decomposition

**v4 Feature Map:**
| v4 Feature | Status | New Behavior |
|------------|--------|--------------|
| 3.6 Ledger handoff sections | ✅ Working | ADD `## Task Breakdown` section |
| 3.8 Governor delegation | ✅ Working | DELEGATE to Work Breakdown agent for complex tasks |

**Conflict Risk:** ✅ NONE — Pure addition, improves consistency

**Resolution Strategy:**

- Create `work-breakdown-specialist.agent.md`
- Define ledger template for task breakdown (status transitions: PENDING → IN_PROGRESS → REVIEW → APPROVED → COMPLETE)
- Add invocation rule to governor: "For Feature pipeline Stage 1, always delegate to Work Breakdown Specialist after Design Planning Architect"

---

### 8. Collector Agent (§6.2)

**Type:** 🆗 NEW (Already implied by Rec #1)

**v4 Features Affected:**

- Same as Rec #1 (Agent Tier Boundaries)

**Impact:**

- Same as Rec #1 — creates Data Collector Specialist agent

**Conflict Risk:** Covered in Rec #1 analysis

---

### 9. Session Logging Implementation (§15 + §5.11-5.14)

**Type:** ✅ FIXES

**v4 Features Affected:**

- Phase 5 (5.11-5.14): Per-session SOLAR activity log

**Impact:**

- **FIXES:** Broken Phase 5 features — no `.github/solar-system/logs/session-*.json` files created during Epic 16 test
- **ROOT CAUSE:** Hooks not creating log files or hook registration incorrect

**v4 Feature Map:**
| v4 Feature | Status | Fix Required |
|------------|--------|--------------|
| 5.11 session-start.cjs log creation | ❌ Not working | Verify hook creates `logs/session-<ts>.json`; check directory permissions |
| 5.12 post-tool-use.cjs event append | ❌ Not working | Verify hook appends JSON events; test with tool call |
| 5.13 stop.cjs termination | ❌ Not working | Verify SESSION_END event written; `.current-session` cleared |
| 5.14 LOG-SOURCES.md | ❌ Not working | Check if file exists; verify content matches plan |

**Conflict Risk:** ✅ NONE — Pure repair of intended v4 functionality

**Resolution Strategy:**

1. **Hook Registration Check:** Verify `hooks.json` lists all 3 hooks with correct paths
2. **Hook Execution Test:** Add debug statements; trigger each hook manually
3. **File System Test:** Verify `solar-system/logs/` directory exists; test write permissions
4. **Root Cause:** Likely hook execution failure or incorrect path resolution

---

## P2 (Medium) & P3 (Low) Recommendations

### P2.9: askQuestion Integration (§9.1)

**Type:** ➕ EXTENDS

**v4 Features Affected:** None (new capability)

**Conflict Risk:** ✅ NONE — Pure addition

---

### P2.10: Approval Workflow (§9.1)

**Type:** ➕ EXTENDS

**v4 Features Affected:**

- Phase 3 (3.6): Ledger handoff sections

**Impact:** ADD `approved: true/false` field to ledger task entries

**Conflict Risk:** ✅ NONE — Pure addition

---

### P2.11: Infinite Loop Prevention (§4.2)

**Type:** ➕ EXTENDS

**v4 Features Affected:**

- Works with Rec #3 (Loop Invocation Mechanism)

**Impact:** ADD iteration counter, timeout, exit condition checks

**Conflict Risk:** ✅ NONE — Pure addition

---

### P2.12: Hook Logging (§11.1)

**Type:** ➕ EXTENDS

**v4 Features Affected:**

- Same as Rec #9 (Session Logging) — both fix Phase 5 logging

**Impact:** Adds logging to ALL hooks, not just session/tool hooks

**Conflict Risk:** ✅ NONE — Pure addition

---

### P3.13-16: Output Verbosity, Installer, Terminal, Model Investigation

**Type:** ➕ EXTENDS or ✅ FIXES

**Conflict Risk:** ✅ NONE — All are polish/fixes, no overwrites

---

## Summary: Feature Impact Matrix

| Recommendation               | Type                  | v4 Features Affected             | Conflict Risk  | Priority |
| ---------------------------- | --------------------- | -------------------------------- | -------------- | -------- |
| P0.1 Agent Tier Boundaries   | 🔄 OVERWRITE + 🆕 NEW | Phase 3 (all), 16 agents         | ⚠️ MODERATE    | CRITICAL |
| P0.2 Orchestrator Delegation | 🔄 OVERWRITE          | Phase 3 (3.6-3.8), Phase 4 (4.5) | ⚠️ HIGH        | CRITICAL |
| P0.3 Loop Invocation         | 🆕 NEW + ➕ EXTEND    | Phase 3 (3.6)                    | ✅ NONE        | CRITICAL |
| P0.4 Memory Consolidation    | 🔄 OVERWRITE          | Phase 1 (1.2-1.3), all agents    | ✅ LOW         | CRITICAL |
| P0.5 Inquiry Gate Repair     | ✅ FIX                | Phase 2 (2.1-2.3)                | ✅ NONE        | CRITICAL |
| P0.6 Learning Capture Fix    | ✅ FIX                | Phase 1 (1.1-1.6)                | ✅ NONE        | CRITICAL |
| P1.5 Workflow Architecture   | 🔄 OVERWRITE (MAJOR)  | Phase 3 (all), Phase 5 (5.3-5.5) | ⚠️ EXTREME     | HIGH     |
| P1.6 Docs Reviewer           | 🆕 NEW                | Review agents                    | ✅ LOW         | HIGH     |
| P1.7 Work Breakdown Agent    | 🆕 NEW + ➕ EXTEND    | Phase 3 (3.6), Phase 4 (4.1)     | ✅ NONE        | HIGH     |
| P1.8 Collector Agent         | 🆕 NEW                | (Same as P0.1)                   | (Same as P0.1) | HIGH     |
| P1.9 Session Logging Fix     | ✅ FIX                | Phase 5 (5.11-5.14)              | ✅ NONE        | HIGH     |
| P2 (9-12)                    | ➕ EXTEND             | Minor additions                  | ✅ NONE        | MEDIUM   |
| P3 (13-16)                   | ➕ EXTEND / ✅ FIX    | Minor fixes                      | ✅ NONE        | LOW      |

---

## Conflict Resolution Recommendations

### CRITICAL: High-Risk Overwrites

**1. Workflow Architecture Migration (P1.5)**

- **Risk:** Breaks entire v4 pipeline system
- **Recommendation:** DEFER to v6; keep pipelines for v5
- **Alternative:** Build workflows in parallel; toggle via config flag

**2. Orchestrator Delegation (P0.2)**

- **Risk:** Removes governor's file-reading capability needed for Router pipeline
- **Recommendation:** Hybrid approach — allow governor to read up to 3 files for classification ONLY; all other context via Collector
- **Alternative:** Strict approach — remove all file reading; accept Router pipeline may misclassify tasks

**3. Agent Tier Boundaries (P0.1)**

- **Risk:** Rewrites all 16 agent instruction bodies; breaks current delegation patterns
- **Recommendation:** Phased rollout:
  - Phase 1: Add tier: frontmatter (non-breaking)
  - Phase 2: Create Collector agent (new capability)
  - Phase 3: Enforce tier rules in governor (breaking)

---

## Implementation Order (Considering Conflicts)

### v5.0 (Safe Changes Only)

**Priority 1 — Pure Fixes (No Conflicts):**

1. ✅ P0.5: Inquiry Gate Repair
2. ✅ P0.6: Learning Capture Activation
3. ✅ P1.9: Session Logging Fix
4. ✅ P0.4: Memory Consolidation (low-risk overwrite)

**Priority 2 — Pure Additions (No Conflicts):** 5. 🆕 P1.6: Dedicated Docs Reviewer 6. 🆕 P1.7: Work Breakdown Agent 7. ➕ P0.3: Loop Invocation Mechanism 8. ➕ P2.10: Approval Workflow 9. ➕ P2.11: Infinite Loop Prevention 10. ➕ P2.12: Hook Logging

### v5.1 (High-Risk Changes — Staged Rollout)

**Priority 3 — Agent Tier Architecture (Phased):** 11. 🔄 P0.1 Phase 1: Add tier: frontmatter to all agents 12. 🆕 P0.1 Phase 2: Create Data Collector Specialist 13. 🔄 P0.2 Hybrid: Governor reads max 3 files for classification, delegates to Collector for deep research

### v6.0 (Major Architecture Change)

**Priority 4 — Workflow Migration (Deferred):** 14. 🔄 P1.5: Workflow Architecture (replace pipelines entirely)

---

## Verification Checklist (Post-Implementation)

For each implemented recommendation, verify:

- [ ] Original v4 feature still works (if intended to preserve)
- [ ] No regression in working v4 features
- [ ] Conflict resolution strategy applied correctly
- [ ] Governor delegation logic updated (if agent changes)
- [ ] Ledger template updated (if new sections added)
- [ ] All agent.md files updated consistently (if tier changes)
- [ ] Documentation updated (AGENTS.md, guides, instructions)

---

**Next Steps:**

1. Prioritize P0 fixes (inquiry gate, learning capture, session logging, memory consolidation)
2. Design phased rollout for agent tier boundaries (P0.1 + P0.2)
3. Create implementation plan for v5.0 (safe changes only)
4. Defer workflow architecture migration to v6.0
