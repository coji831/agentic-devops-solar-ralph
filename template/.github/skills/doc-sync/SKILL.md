# Doc Sync

**Dev Stage**: Document
**Purpose**: Sync and update documentation to reflect completed implementation changes.
**Loaded by**: `docs-curator` when ledger stage = Document

## Steps

1. Read the relevant implementation artifact from `verification-artifacts/` — confirm status=ready; note files changed and summary.
2. Identify documentation targets (populate from sweep findings):
   - [FILL IN: task/story tracking doc, e.g. story BR] — mark completed acceptance criteria.
   - [FILL IN: implementation notes doc] — update with decisions and data shape changes.
   - [FILL IN: architecture overview, e.g. `docs/architecture.md`] — update only if cross-cutting architecture changed.
   - [FILL IN: feature/module design doc] — update if feature logic or data flow changed.
   - [FILL IN: API spec doc] — update if endpoints or contracts changed.
3. Update documentation:
   - Record implementation decisions and data shape changes in relevant docs.
   - Update any "Last Updated" dates in modified docs.
   - Do not add documentation for unchanged code.
4. Write output to `verification-artifacts/{task-id}-docs.json` with schema: `{ "task_id": "", "docs_updated": [], "summary": "" }`.
   - Required compact-handoff fields alongside task-specific fields: `schema_version`, `task_id`, `stage`, `artifact_refs`, `author`, `written_at`. Full schema: `.github/solar-system/schemas/compact-handoff-packet.schema.json`.
5. Append result summary to ledger Decisions Log: `YYYY-MM-DD HH:MM UTC: Documentation complete — {2-sentence summary of docs updated}`.
