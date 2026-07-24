# Implementation

**Dev Stage**: Implement
**Purpose**: Write code changes according to the approved design plan.
**Loaded by**: `implementation-specialist` when ledger stage = Implement

## Steps

1. Extract design plan and context digest from the dispatch prompt — the Governor includes both inline with the file list, approach, and refs.
2. Implement changes:
   - Follow the file list and responsibilities from the design artifact.
   - Follow conventions from `.github/instructions/` files.
   - Keep changes strictly within the Work Package scope — no speculative improvements.
3. Validate:
   - Confirm no hardcoded secrets or environment-specific values in source.
   - Confirm changes stay within the scope defined in the design artifact.
4. Write output to `verification-artifacts/{task-id}-impl.json` with schema: `{ "task_id": "", "files_changed": [], "refs": [] }`.
5. Append result summary to ledger Decisions Log: `YYYY-MM-DD HH:MM UTC: Implementation complete — {2-sentence summary of changes}`.
