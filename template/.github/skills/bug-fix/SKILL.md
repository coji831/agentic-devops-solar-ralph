---
name: bug-fix
description: >-
  Triggered when user asks to fix, debug, or resolve a bug or error
---

# Bug Fix Playbook

**Type**: Playbook — the governor follows this inline; each step dispatches a forked specialist
**Trigger**: User asks to fix, debug, or resolve a bug, error, failure, or unexpected behaviour

## Steps

1. **[Gate: material check]** Confirm a bug description or error trace exists (user prompt, error message, failing test output). If not → use `vscode_askQuestions` to ask for reproduction steps or error details before proceeding.

2. **[Dispatch: data-collector-specialist]** Fork. Task: scan the relevant source paths and any error trace to produce `verification-artifacts/{task-id}-scan.md` (suspected root cause area, affected files, related tests, recent changes). Await artifact.

3. **[Gate: root cause clarity]** Governor reads scan output. If root cause is still ambiguous → dispatch `design-planning-architect` for a short root cause analysis (step 3a). If clear → skip to step 4.

   3a. **[Dispatch: design-planning-architect]** Fork. Task: analyse the scan artifact and produce `verification-artifacts/{task-id}-root-cause.md` (confirmed root cause, reproduction path, change boundary). Await artifact.

4. **[Gate: fix scope approval]** Governor presents the proposed fix scope (one sentence) to the user via `vscode_askQuestions`. If the scope is wrong → return to step 3a with feedback. If approved → record in ledger.

5. **[Dispatch: implementation-specialist]** Fork. Task: apply the minimal fix inside the confirmed change boundary; produce `verification-artifacts/{task-id}-fix.md` (files changed, line-level description of change). Do not refactor or improve code beyond the fix boundary. Await artifact.

6. **[Dispatch: test-specialist]** Fork. Task: add a regression test that would have caught this bug, and confirm all existing related tests pass; produce `verification-artifacts/{task-id}-tests.md` (test added + pass confirmation). Await artifact.

7. **[Gate: test pass check]** If tests fail → re-dispatch `implementation-specialist` or `test-specialist` with failure details (Ralph loop, max 3 iterations per lane).

8. **[Gate: adversarial verify]** Governor selects a non-author specialist by domain match (prefer `review-auditor`). Fork. Task: verify the fix is complete, does not introduce regressions, and the regression test is meaningful; produce `verification-artifacts/{task-id}-verify.md` (verdict: `APPROVED` or `REJECTED` + reasoning). Await artifact.

9. **[Gate: verdict check]** If `REJECTED` → return to `implementation-specialist` with findings (Ralph loop, max 3 iterations). If `APPROVED` → continue.

10. **[Exit]** Append `[CLOSED] bug-fix — exit criteria met` to ledger Decisions Log. Delete `verification-artifacts/{task-id}-*.md`. Set Work Queue row to `CLOSED`.
