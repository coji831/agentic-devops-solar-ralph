---
name: review
description: "Use when reviewing changes for regressions, correctness, security, and missing coverage. Generic — no stack assumptions. Stack context loaded from the project's .instructions.md at runtime."
argument-hint: "Artifact path and task-id to review"
user-invocable: false
---

# Review

**Dev Stage**: Review
**Purpose**: Challenge the output of a previous stage — identify gaps, regressions, and unmet exit criteria — and return a verdict before TASK_COMPLETE is emitted.
**Loaded by**: `review-auditor` when ledger stage = VERIFY

## When to Use

- At the VERIFY stage, dispatched by the Governor as a non-author auditor
- When a design, implementation, or test artifact needs adversarial challenge before closure
- When a REJECTED verdict from a previous review cycle requires a re-audit after remediation

## Procedure

1. Read the artifact under review: `verification-artifacts/{task-id}-{type}.md` (status: ready).
2. Read the exit_criteria from the ledger Loop State.
3. Check each exit criterion — mark as met or unmet with specific evidence.
4. Challenge assumptions: are there edge cases not covered? Are there regressions introduced? Are there security or data-integrity risks?
5. Check that no scope has been silently expanded beyond the design artifact.
6. Write verdict to `verification-artifacts/{task-id}-verify.md`:
   - `APPROVED` — all exit criteria met, no blocking findings
   - `REJECTED` — list each blocking finding with specific location and reason
7. Append verdict line to ledger Decisions Log.
8. Do not attempt to fix findings — record them and return to the Governor.

## Output

- `verification-artifacts/{task-id}-verify.md` — verdict (APPROVED or REJECTED), exit criteria check, findings list
