---
name: solar-cleanup-learning
description: "Archive unpromoted learning entries and reset PATTERNS.md and ERRORS.md for the next task or epic. Preserves last 3 months of archives."
model: "Claude Sonnet 4.6 (copilot)"
---

# /cleanup-learning

Archive unpromoted PATTERNS.md and ERRORS.md entries after a task or epic completes, and reset the files for the next task.

## Usage

```
/cleanup-learning <scope>
```

Scope options:
- `task` — Archive entries added during the current task only (entries since last cleanup)
- `epic` — Archive all entries related to the current epic
- `all` — Archive ALL unpromoted entries in both PATTERNS.md and ERRORS.md

---

## Agent Instructions

You are the learning cleanup agent for this repository.

### Step 1 — Read Current State

Read:
- `.github/solar-system/.learnings/PATTERNS.md`
- `.github/solar-system/.learnings/ERRORS.md`
- `.github/.ai_ledger.md` (to identify current task/epic context for scoped cleanup)

### Step 2 — Identify Entries to Archive

Based on the scope:

- **task**: Entries with a date matching the current session date or entries tagged with the current task ID in the ledger
- **epic**: Entries referencing the current epic number or added since epic start date
- **all**: All remaining entries not already marked `[ARCHIVED]` or `<!-- ... archived ... -->`

Generate a **Cleanup Preview** and ask for confirmation before deleting anything:

```
## Cleanup Preview — [SCOPE] — [DATE]

### Entries to Archive (not promoted)

| # | Source | Entry ID | Date Added | Reason to Archive |
|---|--------|----------|------------|-------------------|
| 1 | PATTERNS.md | [ID] | [date] | Task-specific, not reusable |
| 2 | ERRORS.md | [ID] | [date] | Already covered in instructions |

### Entries to KEEP (not archived — require manual review)

| # | Source | Entry ID | Reason to Keep |
|---|--------|----------|----------------|
| 1 | PATTERNS.md | [ID] | Still active / referenced by open task |

Total: [N] entries to archive, [M] entries to keep
```

Ask: "Proceed with archiving [N] entries?" (Yes / No / Review each one)

### Step 3 — Archive Entries

For each confirmed entry:

1. Read the learning archive file for the current month: `.github/solar-system/.learnings/learning-archive-[YYYY-MM].md`
   - If it does not exist: create it with header `# Learning Archive — [MONTH YEAR]`
2. Append the full entry text to the archive file under section `## Archived (not promoted) — [DATE]`
3. Replace the original entry in PATTERNS.md or ERRORS.md with:
   ```
   <!-- [ID] archived [DATE] — not promoted (task-specific / scope: [scope]) -->
   ```

### Step 4 — Reset Files

After archiving:

1. Remove all `<!-- ... archived ... -->` placeholder lines from PATTERNS.md and ERRORS.md (these were created by prior promotes and cleanups)
2. If PATTERNS.md or ERRORS.md is now effectively empty (only has the header/template), leave the header intact — do NOT delete the file

### Step 5 — Expire Old Archives (3-Month Retention)

Check the `.github/solar-system/.learnings/` directory for archive files older than 3 months:
- Archive files follow the pattern: `learning-archive-YYYY-MM.md`
- If any archive file's date is more than 3 months before today's date: flag it for deletion

**Do NOT auto-delete.** Ask the user: "Archive file `learning-archive-[YYYY-MM].md` is older than 3 months. Delete it?" Require explicit confirmation before deletion.

### Step 6 — Summary

Output a concise cleanup summary:

```
## Cleanup Complete — [SCOPE] — [DATE]

- Archived: [N] entries → learning-archive-[YYYY-MM].md
- Kept: [M] entries remain active
- PATTERNS.md reset: [Yes / No — N entries remain]
- ERRORS.md reset: [Yes / No — N entries remain]
- Archive files flagged for expiry: [N files or "none"]
```

---

## Constraints

- Never delete entries without archiving them first.
- Never delete archive files without explicit user confirmation.
- Never reset a file that still has active (non-archived) entries the user hasn't confirmed for archival.
- If scope is ambiguous (e.g., mixed task and epic entries): default to `task` scope and ask for confirmation before expanding.
