# Data Collection

**Dev Stage**: Scan
**Purpose**: Gather task context, repository state, and raw input findings for the next pipeline stage.
**Loaded by**: `data-collector-specialist` when ledger stage = Scan

## Steps

1. Extract task context from the dispatch prompt — the Governor includes the Context Summarizer's digest inline with facts, refs, and warnings.
2. Build findings:
   - List impacted files and their current state from the digest refs.
   - Note any conflicts, dependencies, or constraints discovered.
   - Flag any out-of-scope items as `BLOCKED: OUT_OF_SCOPE: <description>` — do NOT include them in the artifact.
3. Write output to `verification-artifacts/{task-id}-scan.json` with schema: `{ "task_id": "", "refs": [], "impacted_files": [], "out_of_scope_flags": [] }`.
4. Append result summary to ledger Decisions Log: `YYYY-MM-DD HH:MM UTC: Scan complete — {2-sentence summary of key findings}`.
