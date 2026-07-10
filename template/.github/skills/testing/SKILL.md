# Testing

**Dev Stage**: Test
**Purpose**: Write and run tests for implemented changes.
**Loaded by**: `test-specialist` when ledger stage = Test

⚠️ **Requires `{TEST_RUNNER}` configuration before use.** Verify test config file is present and `execute` tool can run `{TEST_RUNNER}` before dispatching.

## Steps

1. Read `verification-artifacts/{task-id}-impl.json` — confirm status=ready; note files changed.
2. Identify test targets:
   - For each changed file, locate or create the corresponding test file using `{TEST_RUNNER}` naming conventions.
   - Review existing tests to avoid duplication and match existing test style.
3. Write tests:
   - Cover the happy path for each changed function/component.
   - Add at least one edge case per Acceptance Criterion from the Work Package.
   - Add framework-specific patterns at install time (e.g. RTL role/text queries for React, mock patterns for the stack).
4. Run tests:
   - Execute: `npx {TEST_RUNNER} run` (or the framework's equivalent run command).
   - If tests fail: attempt one fix pass → if still failing, emit `BLOCKED: test failures — remediation needed` and return to Governor.
5. Write output to `verification-artifacts/{task-id}-test.json` with schema: `{ "task_id": "", "tests_added": [], "tests_passed": 0, "tests_failed": 0, "coverage_notes": "", "status": "pass|fail|partial" }`.
   - Required compact-handoff fields alongside task-specific fields: `schema_version`, `task_id`, `stage`, `artifact_refs`, `author`, `written_at`. Full schema: `.github/solar-system/schemas/compact-handoff-packet.schema.json`.
6. Append result summary to ledger Decisions Log: `YYYY-MM-DD HH:MM UTC: Testing complete — {pass/fail counts and key coverage note}`.
