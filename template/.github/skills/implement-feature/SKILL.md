---
name: implement-feature
description: Full Scan → Plan + Design → Implement → Test → Document pipeline for implementing a new feature or adding functionality to the codebase.
---

# Implement Feature

**Type**: Playbook (governor follows inline; each step dispatches a forked specialist)
**Trigger**: User asks to implement, build, or add a feature

## Steps

1. **[Gate: material check]** Verify input materials are ready in ledger. Confirm `exit_criteria` is defined in Work Queue. If not → emit MATERIAL_INSUFFICIENT, do not proceed.

2. **[Dispatch: Data Collector Specialist]** Dispatch `data-collector-specialist.agent.md` as a subagent.
   - SKILL: `.github/skills/data-collection/SKILL.md`
   - Result path: `verification-artifacts/{task-id}-scan.json`
   - Return instruction: "Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."
   - Await artifact → `verification-artifacts/{task-id}-scan.json`.

3. **[Dispatch: Design Planning Architect]** Dispatch `design-planning-architect.agent.md` as a subagent.
   - SKILL: `.github/skills/design-planning/SKILL.md`
   - Result path: `verification-artifacts/{task-id}-design.json`
   - Return instruction: "Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."
   - Await artifact → `verification-artifacts/{task-id}-design.json`.

4. **[Gate: design approval]** Governor checks design output. If `config.human_approval = true` → use `vscode_askQuestions` to get user confirmation before proceeding. If rejected or changes requested → re-dispatch `design-planning-architect` with feedback (Ralph loop, max 3 iterations per `recursive-remediation` SKILL.md).

5. **[Gate: adversarial verify — design]** Governor dispatches `design-planning-architect` as non-author auditor (alternate approach challenge) → verify design artifact → verdict APPROVED or REJECTED. On REJECTED → return to design agent with rejection reasons.

6. **[Dispatch: Implementation Specialist]** Dispatch `implementation-specialist.agent.md` as a subagent.
   - SKILL: `.github/skills/implementation/SKILL.md`
   - Result path: `verification-artifacts/{task-id}-impl.json`
   - Return instruction: "Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."

7. **[Gate: adversarial verify — implementation]** Governor dispatches `review-auditor.agent.md` → verify implementation artifact → verdict APPROVED or REJECTED. On REJECTED → re-dispatch with feedback via `recursive-remediation` SKILL.md.

8. **[Dispatch: Test Specialist]** Dispatch `test-specialist.agent.md` as a subagent.
   - SKILL: `.github/skills/testing/SKILL.md`
   - Result path: `verification-artifacts/{task-id}-test.json`
   - Return instruction: "Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."

9. **[Gate: adversarial verify — tests]** Governor dispatches `review-auditor.agent.md` → verify test artifact → verdict APPROVED or REJECTED. On REJECTED → remediate via `recursive-remediation` SKILL.md.

10. **[Dispatch: Docs Curator]** Dispatch `docs-curator.agent.md` as a subagent.
    - SKILL: `.github/skills/doc-sync/SKILL.md`
    - Result path: `verification-artifacts/{task-id}-docs.json`
    - Return instruction: "Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."

11. **[Exit]** If all stages APPROVED → update ledger CLOSED. Archive ledger. Reset from template. Clean up `verification-artifacts/{task-id}-*` task files. If any stage REJECTED × 3 → append `BLOCKED: ESCALATION_REQUIRED` to Decisions Log and pause for human review.
