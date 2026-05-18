# Data Collection

**Dev Stage**: Scan
**Purpose**: Gather task context, repository state, and raw input findings for the next pipeline stage.
**Loaded by**: `data-collector-specialist` when ledger stage = Scan

## Steps

1. Read `verification-artifacts/{task-id}-input.json` — confirm status=ready and exit_criteria are defined.
2. Scan relevant source files:
   - Read repo entry points and feature folders (max 10 reads total).
   - Identify files directly related to the task scope from the Work Package.
   - Note existing patterns, types, and interfaces relevant to the task.
3. Collect findings:
   - List impacted files and their current state.
   - Note any conflicts, dependencies, or constraints discovered.
   - Flag any out-of-scope items as `BLOCKED: OUT_OF_SCOPE: <description>` — do NOT include them in the artifact.
4. Write output to `verification-artifacts/{task-id}-scan.json` with schema: `{ "task_id": "", "findings": [], "impacted_files": [], "constraints": [], "out_of_scope_flags": [] }`.
5. Append result summary to ledger Decisions Log: `YYYY-MM-DD HH:MM UTC: Scan complete — {2-sentence summary of key findings}`.
