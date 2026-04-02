# Governor Haiku Fix Plan

**Status:** Complete — all P1–P7 applied.
**Source:** Research findings from `docs/research/improving-low-reasoning-model-performance.md`
**Scope:** 7 fixes to the orchestration governor and specialist agents identified from Claude Haiku 4.5 run analysis.

---

## P1 — Stage 4 File Pattern Gate

**Problem:** Stage 4 (Security Auditor) skipped or invoked based on qualitative judgment. Models interpret "security-relevant" inconsistently.

**Fix:** Replace qualitative skip condition with a binary file pattern checklist. If any changed file path matches any pattern → Stage 4 is mandatory.

**Patterns:** `*route*`, `*auth*`, `*middleware*`, `*config*`, `*controller*`, `*permission*`, `*secret*`, `*credential*`

**Target:** `orchestration-governor.agent.md` — pipeline selection or step supervision section.

**ACs:**

- [x] Stage 4 is triggered automatically when any changed file matches the pattern list
- [x] Stage 4 is skipped only when no file matches — no other judgment allowed
- [x] Pattern list is visible inline in the governor (not referenced externally)

---

## P2 — Remove Model Label from Delegation Line

**Problem:** `| model: <model>` in delegation indicator line is wrong the majority of the time — Task tool does not reliably read subagent frontmatter at dispatch (platform bug, GitHub issues #18873, #19402).

**Fix:** Remove `| model: <model>` segment from the delegation step indicator.

**Before:** `🤖 Delegating → <Agent Name>  |  model: <model>  (Stage <N>: <stage label>)`
**After:** `🤖 Delegating → <Agent Name>  (Stage <N>: <stage label>)`

**Target:** `orchestration-governor.agent.md` — step indicator lookup table.

**ACs:**

- [x] Delegation indicator no longer contains `model:` token
- [x] Agent name and stage label are still present
- [x] No other indicator lines are altered

---

## P3 — No Specialist Before Context Read Gate

**Problem:** Governor's thinking block pre-selects a specialist before reading the ledger or story docs — agentic impulse behavior causing Stage 1 skips.

**Fix:** Add an explicit gate in the governor `<approach>` section: the `agent` tool may not be called until the ledger, AGENTS.md, and the story BR/implementation docs have been read in the current session.

**Target:** `orchestration-governor.agent.md` — `<approach>` step 1.

**ACs:**

- [x] Gate is stated as a hard rule, not advisory language ("must not", not "should")
- [x] Minimum required reads are listed: ledger + AGENTS.md + story BR + story implementation doc
- [x] Gate appears before any delegation instructions

---

## P4 — Ledger Write Template in Output Format

**Problem:** At pipeline close, governor writes ledger entries that drift from the expected schema — instruction decay in long sessions causes field omissions.

**Fix:** Add a concrete ledger write template (exact field names) to the governor `<output_format>` section. Governor must populate all fields before closing.

**Fields to include:** session ID, pipeline type, stage outcomes, final verdict, blockers, WORK_PACKAGE_COMPLETE marker.

**Target:** `orchestration-governor.agent.md` — `<output_format>` section.

**ACs:**

- [x] Template is provided as a literal block (not prose description)
- [x] All required ledger fields are listed
- [x] WORK_PACKAGE_COMPLETE marker placement is specified

---

## P5 — grep_search Preference in Specialist Agents

**Problem:** `semantic_search` hangs for up to 7 minutes in nested subagent environments (confirmed VS Code bug, issue #299102). Worse in multi-root workspaces.

**Fix:** Add a search preference rule to all specialist agents: use `grep_search` and `file_search` by default; use `semantic_search` only as last resort when exact text or filename patterns are unknown.

**Target files:**

- `backend-implementation-specialist.agent.md`
- `frontend-implementation-specialist.agent.md`
- `backend-test-specialist.agent.md`
- `frontend-test-specialist.agent.md`
- `implementation-specialist.agent.md`
- `backend-review-auditor.agent.md`
- `frontend-review-auditor.agent.md`
- `security-auditor.agent.md`
- `bug-investigation-specialist.agent.md`
- `cache-external-integration-specialist.agent.md`
- `docs-curator.agent.md`
- `release-readiness-specialist.agent.md`

**ACs:**

- [x] Rule added to all 12 specialist agent files
- [x] Rule is in a consistent location (tools or approach section)
- [x] Phrasing is identical or near-identical across all files

---

## P6 — PreToolUse Hook for Stage 1 Enforcement

**Problem:** Stage 1 (Design Planning Architect) is skipped by the governor jumping directly to implementation — agentic impulse. Not fixable by prompting alone; requires a mechanical gate.

**Fix:** New PreToolUse hook that checks whether the ledger contains a Stage 1 entry before any `agent` tool call that targets an implementation or test specialist. If no Stage 1 entry exists, the hook blocks and injects a redirect message.

**Target:** New file `.github/hooks/pre-tool-use.cjs` + new entry in `hooks.json`.

**ACs:**

- [x] Hook fires on `agent` tool calls only (not other tools)
- [x] Hook reads ledger for Stage 1 completion marker
- [x] Hook blocks call and returns a redirect message if Stage 1 is absent
- [x] Hook passes through if Stage 1 is present or if the target is the Design Architect itself
- [x] `hooks.json` updated with `PreToolUse` entry pointing to new file

---

## P7 — Remove Skill-Loading from Governor Delegation

**Problem:** Governor loads specialist skills before delegating — adds 8-15k tokens to governor context that are consumed once and never freed (context malloc/free problem). Accelerates instruction decay past the 20-32k threshold.

**Fix:** Verify that skill `read_file` calls are absent from governor delegation blocks. Skills should only be loaded inside the specialist receiving the delegation.

**Target:** `orchestration-governor.agent.md` — all delegation blocks.

**ACs:**

- [x] No `read_file` calls for SKILL.md files appear in governor instructions
- [x] Governor delegates by name only; skill loading is the specialist's responsibility
- [x] If skill references exist, they are removed without replacement in the governor

---

## Delivery Order

| Priority | Fix                                | Target         | Effort            |
| -------- | ---------------------------------- | -------------- | ----------------- | ------------------------------- |
| P1       | File pattern gate for Stage 4      | governor       | Low               | ✅ Done                         |
| P2       | Remove model label from delegation | governor       | Low               | ✅ Already applied              |
| P3       | No specialist before context read  | governor       | Low               | ✅ Done                         |
| P4       | Ledger write template              | governor       | Medium            | ✅ Done                         |
| P5       | grep_search preference             | 12 agent files | Medium            | ✅ Done                         |
| P6       | PreToolUse hook                    | new hook file  | High              | ✅ Done                         |
| P7       | Remove skill-loading from governor | governor       | Low (verify only) | ✅ Verified — nothing to remove |

P1–P4 and P7 can be applied to the governor in one batch. P5 requires a sweep of all specialist agents. P6 is a separate implementation task.
