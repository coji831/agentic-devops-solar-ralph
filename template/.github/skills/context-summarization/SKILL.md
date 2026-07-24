# Context Summarization

**Dev Stage**: Scan (context-gathering step before any specialist dispatch)
**Purpose**: Read source files and produce a compact digest that the next specialist consumes instead of reading files directly.
**Loaded by**: `context-summarizer` when Governor dispatches before a specialist stage

## Steps

1. Read the dispatch prompt — extract the list of files/paths to investigate and the target specialist type.
2. For each target file or path:
   - Read key sections (entry points, interfaces, function signatures, relevant types).
   - Do NOT read full file bodies — use `startLine/endLine` for targeted reads.
   - Note file path, key exports, relevant patterns.
3. Build a compact digest:
   - `task_id` — the current work item ID.
   - `target_specialist` — which specialist this digest is for.
   - `refs[]` — array of `{path, section, relevance}` objects pointing to source files.
   - `facts[]` — bullet-point key facts the specialist needs to know (max 10 bullets, 1 line each).
   - `warnings[]` — anything the specialist should be cautious about.
4. Write output to `verification-artifacts/{task-id}-digest.json` with schema: `{ "task_id": "", "target_specialist": "", "refs": [], "facts": [], "warnings": [] }`.
5. Append digest summary to ledger Decisions Log: `YYYY-MM-DD HH:MM UTC: Context gathered for {specialist} — {1-sentence summary of key facts delivered}`.
