---
name: testing
description: "Use when adding or repairing tests — unit, integration, or component. Generic — no stack assumptions. Stack context loaded from the project's .instructions.md at runtime."
argument-hint: "Implementation artifact path and task-id to test"
user-invocable: false
---

# Testing

**Dev Stage**: Test
**Purpose**: Write or repair tests to verify the implementation against the exit criteria in the ledger.
**Loaded by**: `test-specialist` when ledger stage = Test

## When to Use

- After an implementation artifact has been produced
- When new behavior requires test coverage before the VERIFY stage
- When existing tests fail after implementation and must be repaired

## Procedure

1. Read `verification-artifacts/{task-id}-impl.md` (status: ready) to know what changed.
2. Load any path-specific `.instructions.md` files that specify test runner, conventions, or file paths.
3. Identify the changed behavior to verify — map each exit criterion to at least one test case.
4. Write tests for: happy path + at least one edge case per exit criterion.
5. Run tests; record results (pass / fail / error) and the exact command used.
6. Do not modify source code to make tests pass — if source must change, emit ESCALATION_REQUIRED to the orchestrator.
7. Write output to `verification-artifacts/{task-id}-qa.md` — verdict (PASS / FAIL), test command, counts, any failures.
8. Append result summary to ledger Decisions Log.

## Output

- New or updated test files
- `verification-artifacts/{task-id}-qa.md` — verdict, test command, pass/fail counts, failure details if any
