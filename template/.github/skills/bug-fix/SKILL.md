---
name: bug-fix
description: Scan → Design → Implement → Test pipeline to locate and resolve a specific bug, error, or regression in the codebase.
---

# Bug Fix

**Type**: Playbook (governor follows inline; each step dispatches a forked specialist)
**Trigger**: User asks to fix, debug, or resolve a bug or error

## Steps

1. **[Gate: material check]** Verify input materials are ready in ledger. Confirm `exit_criteria` includes the bug reproduction case or error description. If not → emit MATERIAL_INSUFFICIENT, do not proceed.

2. **[Dispatch: Data Collector Specialist]** Dispatch `data-collector-specialist.agent.md` as a subagent to locate the bug.
   - SKILL: `.github/skills/data-collection/SKILL.md`
   - Result path: `verification-artifacts/{task-id}-scan.json`
   - Return instruction: "Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."
   - Await artifact → `verification-artifacts/{task-id}-scan.json` (must include root cause hypothesis).

3. **[Dispatch: Design Planning Architect]** Dispatch `design-planning-architect.agent.md` as a subagent with the root cause from scan.
   - SKILL: `.github/skills/design-planning/SKILL.md`
   - Result path: `verification-artifacts/{task-id}-design.json`
   - Return instruction: "Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."
   - Design artifact must include the fix plan and rationale.

4. **[Gate: design approval]** Governor checks fix plan. If `config.human_approval = true` → use `vscode_askQuestions` to confirm before proceeding. If rejected or changes requested → re-dispatch `design-planning-architect` with feedback (Ralph loop, max 3 iterations per `recursive-remediation` SKILL.md).

5. **[Dispatch: Implementation Specialist]** Dispatch `implementation-specialist.agent.md` as a subagent to apply the fix.
   - SKILL: `.github/skills/implementation/SKILL.md`
   - Result path: `verification-artifacts/{task-id}-impl.json`
   - Return instruction: "Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."

6. **[Gate: adversarial verify — fix]** Governor dispatches `review-auditor.agent.md` → verify implementation artifact → verdict APPROVED or REJECTED. On REJECTED → re-dispatch with feedback via `recursive-remediation` SKILL.md.

7. **[Dispatch: Test Specialist]** Dispatch `test-specialist.agent.md` as a subagent to confirm the fix and add a regression test.
   - SKILL: `.github/skills/testing/SKILL.md`
   - Result path: `verification-artifacts/{task-id}-test.json`
   - Return instruction: "Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."
   - Test must include a regression test that would have caught the original bug.

8. **[Gate: adversarial verify — tests]** Governor dispatches `review-auditor.agent.md` → verify test artifact → verdict APPROVED or REJECTED. On REJECTED → remediate via `recursive-remediation` SKILL.md.

9. **[Exit]** If all stages APPROVED → update ledger CLOSED. Archive ledger. Reset from template. Clean up `verification-artifacts/{task-id}-*` task files. If any stage REJECTED × 3 → append `BLOCKED: ESCALATION_REQUIRED` to Decisions Log and pause for human review.
