# Implementation

**Dev Stage**: Implement
**Purpose**: Write code changes according to the approved design plan.
**Loaded by**: `implementation-specialist` when ledger stage = Implement

## Steps

1. Read `verification-artifacts/{task-id}-design.json` — confirm status=ready and design is approved.
2. Implement changes:
   - Follow the file list and responsibilities from the design artifact.
   - Follow conventions from `.github/instructions/` files.
   - Keep changes strictly within the Work Package scope — no speculative improvements.
3. Validate:
   - Confirm no hardcoded secrets or environment-specific values in source.
   - Confirm changes stay within the scope defined in the design artifact.
4. Write output to `verification-artifacts/{task-id}-impl.json` with schema: `{ "task_id": "", "files_changed": [], "summary": "", "notes": "" }`.
   - Required compact-handoff fields alongside task-specific fields: `schema_version`, `task_id`, `stage`, `artifact_refs`, `author`, `written_at`. Full schema: `.github/solar-system/schemas/compact-handoff-packet.schema.json`.
5. Append result summary to ledger Decisions Log: `YYYY-MM-DD HH:MM UTC: Implementation complete — {2-sentence summary of changes}`.
