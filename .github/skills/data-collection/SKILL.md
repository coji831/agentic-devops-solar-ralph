---
name: data-collection
description: "Use when gathering files, running searches, and producing a structured context manifest for other agents. Read-only — never writes code or makes design decisions."
argument-hint: "What context to collect and for which task-id"
user-invocable: false
---

# Data Collection

**Dev Stage**: Scan
**Purpose**: Locate, read, and summarize relevant files into a structured manifest without making design decisions.
**Loaded by**: `data-collector-specialist` when ledger stage = Scan

## When to Use

- At the start of any new task before planning or implementation begins
- When an agent needs targeted context from the codebase without reading files itself
- When the scope of a task is unclear and evidence must be gathered first

## Procedure

1. Read the collection task from `## Handoff Payload` in `.github/.ai_ledger.md`.
2. Use `grep_search` and `file_search` to locate relevant files without reading them yet.
3. Prioritize files most directly relevant to the task — read the most relevant first.
4. For each file read: record path, purpose, and relevant content (1–3 sentences max per file).
5. Stop when the requested context is collected OR the 10-file read limit is reached — whichever comes first. If more than 10 files appear relevant, categorize by directory/module and stop at the boundary.
6. Write collected context as a structured manifest to `verification-artifacts/{task-id}-scan.md`.
7. Append result summary to ledger Decisions Log.

## Output

- `verification-artifacts/{task-id}-scan.md` — structured manifest: file paths, purposes, relevant excerpts
- No design conclusions, no recommendations, no architectural judgments
