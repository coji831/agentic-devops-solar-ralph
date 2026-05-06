---
name: implement-feature
description: >-
  Triggered when user asks to implement, build, or add a feature
---

# Implement Feature Playbook

**Type**: Playbook — the governor follows this inline; each step dispatches a forked specialist
**Trigger**: User asks to implement, build, or add a feature or capability

## Steps

1. **[Gate: material check]** Confirm a clear feature description exists (user prompt or linked doc). If not → emit `MATERIAL_INSUFFICIENT` to governor; do not proceed.

2. **[Dispatch: data-collector-specialist]** Fork. Task: scan the relevant source paths to produce `verification-artifacts/{task-id}-scan.md` (existing structure, dependencies, affected files, potential conflicts). Await artifact.

3. **[Gate: scan review]** Governor reads scan output. If scope is too large or blockers are found → use `vscode_askQuestions` to clarify with user before continuing.

4. **[Dispatch: design-planning-architect]** Fork. Task: produce `verification-artifacts/{task-id}-design.md` (file-level change plan, interfaces, no-scope list). Await artifact.

5. **[Gate: design approval]** Governor presents design summary to user via `vscode_askQuestions`. If rejected → re-dispatch `design-planning-architect` with feedback (Ralph loop, max 3 iterations). If approved → record `APPROVED` in ledger.

6. **[Dispatch: implementation-specialist]** Fork. Task: execute the design artifact change plan; produce `verification-artifacts/{task-id}-impl.md` (files changed + brief description). Await artifact.

7. **[Dispatch: test-specialist]** Fork. Task: write or update tests covering the new behaviour; produce `verification-artifacts/{task-id}-tests.md` (test files created/updated + pass confirmation). Await artifact.

8. **[Gate: test pass check]** If tests fail → re-dispatch `implementation-specialist` or `test-specialist` with failure details (Ralph loop, max 3 iterations per lane).

9. **[Dispatch: docs-curator]** Fork. Task: update file headers, design docs, or architecture notes affected by the change; produce `verification-artifacts/{task-id}-docs.md`. Await artifact.

10. **[Gate: adversarial verify]** Governor selects a non-author specialist from the Agent Registry by domain match (prefer `review-auditor` for code output). Fork. Task: challenge assumptions, completeness, and edge cases in `{task-id}-impl.md` and `{task-id}-tests.md`; produce `verification-artifacts/{task-id}-verify.md` (verdict: `APPROVED` or `REJECTED` + specific reasoning). Await artifact.

11. **[Gate: verdict check]** If `REJECTED` → governor returns the task to the producing agent with the specific review findings (Ralph loop, max 3 iterations). If `APPROVED` → continue.

12. **[Exit]** Append `[CLOSED] implement-feature — exit criteria met` to ledger Decisions Log. Delete `verification-artifacts/{task-id}-*.md`. Set Work Queue row to `CLOSED`.
