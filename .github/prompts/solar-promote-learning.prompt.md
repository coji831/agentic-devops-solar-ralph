---
name: solar-promote-learning
description: "Promote specific PATTERNS.md or ERRORS.md entries to permanent files (instructions, workflows, or skill docs) using the format converters in .learnings/converters/."
model: "Claude Sonnet 4.6 (copilot)"
---

# /promote-learning

Promote accumulated learning entries from `.github/solar-system/.learnings/PATTERNS.md` or `ERRORS.md` into permanent governance files.

## Usage

```
/promote-learning <id1,id2,id5>
```

Provide the entry IDs (date-title slug or entry number) you want to promote. Example:
```
/promote-learning 2026-04-22-scope-creep,2026-04-22-cookie-proxy
```

If no IDs are provided, the agent will scan PATTERNS.md and ERRORS.md and generate a **Promotion Report** listing all promotable candidates with suggested destinations.

---

## Agent Instructions

You are the learning promotion agent for this repository.

### Step 1 — Read Source Files

Read `.github/solar-system/.learnings/PATTERNS.md` and `.github/solar-system/.learnings/ERRORS.md`.

### Step 2 — Identify Entries to Promote

If specific IDs were provided: locate those entries and skip to Step 3.

If no IDs were provided: scan both files and generate a **Promotion Report**:

```
## Promotion Report — [DATE]

### Promotable Entries

| # | Source | Entry ID | Suggested Destination | Converter | Priority |
|---|--------|----------|----------------------|-----------|----------|
| 1 | PATTERNS.md | [ID] | [target file] | patterns-to-instructions | HIGH |
| 2 | ERRORS.md | [ID] | [target file] | errors-to-instructions | MEDIUM |

### Reasoning
[One sentence per entry explaining why it qualifies for permanent promotion]

### Entries NOT Recommended for Promotion
[List entries that are too task-specific or already covered elsewhere]
```

Ask the user: "Which entries should I promote? Reply with entry numbers (e.g., `1,3,5`) or `all`."

### Step 3 — Duplicate Detection

Before converting each entry, read the target file and check for existing content using the rule from `.github/solar-system/.learnings/converters/README.md`:

- Search for 2 of the 3 main keywords from the entry title in the target file
- If 2+ keywords found: flag as `DUPLICATE_CANDIDATE` and ask: "A similar entry may already exist in [target file]. Promote anyway, update existing, or skip?"

### Step 4 — Convert and Insert

For each confirmed entry, use the appropriate converter template from `.github/solar-system/.learnings/converters/`:

| Source → Destination | Converter file |
|---|---|
| PATTERNS.md → instructions | `converters/patterns-to-instructions.md` |
| PATTERNS.md → workflow | `converters/patterns-to-workflow.md` |
| PATTERNS.md → skill | `converters/patterns-to-skill.md` |
| ERRORS.md → instructions | `converters/errors-to-instructions.md` |

Read the applicable converter file, follow its **Input → Output** format exactly, and insert the converted content into the correct target file at the placement location specified by the converter.

All inserted content must include the cross-reference comment:
```
<!-- Source: PATTERNS.md #[ENTRY-ID] — promoted [DATE] -->
```

### Step 5 — Archive Promoted Entries

After successful insertion, archive each promoted entry:

1. Read the learning archive file for the current month: `.github/solar-system/.learnings/learning-archive-[YYYY-MM].md`
   - If it does not exist: create it with header `# Learning Archive — [MONTH YEAR]`
2. Append the full entry text to the archive file
3. Delete the promoted entry from PATTERNS.md or ERRORS.md
   - Replace the entry with a single-line marker: `<!-- [ID] archived [DATE] → promoted to [target file] -->`

### Step 6 — Summary

Output a concise promotion summary:

```
## Promotion Complete — [DATE]

| Entry | Destination | Status |
|-------|-------------|--------|
| [ID] | [target file] | ✅ Promoted |
| [ID] | [target file] | ⏭️ Skipped (duplicate) |

Archive: .github/solar-system/.learnings/learning-archive-[YYYY-MM].md
```

---

## Constraints

- Never promote an entry that is task-specific and will not apply to future work.
- Never duplicate existing instructions — check first, update if better, skip if equivalent.
- Never delete entries without archiving them first.
- If the converter template does not clearly fit the entry: stop and ask the user which converter to use.
