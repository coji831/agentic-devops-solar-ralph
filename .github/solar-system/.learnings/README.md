# SOLAR Learning System

Three-category system for capturing and promoting knowledge across sessions.

---

## Categories

### PATTERNS.md — Implementation Patterns

Lessons extracted from implementation struggles (2+ iterations on the same problem, non-obvious solutions, platform quirks that took >1 hour to resolve).

**Written by:** Any specialist agent after completing a task that required 2+ rework cycles.

**Format:**

```
### [DATE] [CATEGORY] — [SHORT TITLE]
**Problem:** <what went wrong or was unclear>
**Solution:** <how it was resolved>
**Lesson:** <the reusable rule or pattern to apply next time>
```

Categories: `convention`, `architecture`, `tooling`, `pattern`, `gotcha`, `security`

**Injected at:** Session start by the `SessionStart` hook (condensed summary, up to 20 lines).

---

### ERRORS.md — Platform & Tool Failures

Observed tool failures, hook execution errors, and platform limitations with corrective actions. Blocking enforcement — write an entry here whenever a tool behaves unexpectedly.

**Written by:** Any agent when a tool/platform error is encountered.

**Format:**

```
### [DATE] [TOOL NAME] — [SHORT DESCRIPTION]
**Error:** <exact error message or behaviour observed>
**Context:** <what task was in progress>
**Root Cause:** <why the failure occurred>
**Corrective Action:** <what was done to resolve it>
**Prevention:** <rule or check to avoid recurrence>
```

---

### LOGS — Session Activity (gitignored)

Ephemeral session activity logs (`session-*.json`). Created by the `SessionStart` hook and written by `PostToolUse`. Not committed to the repo — used for debugging only.

---

## Promotion Workflow

1. After a task completes, the orchestrator scans PATTERNS.md and ERRORS.md for new entries.
2. Entries are classified: HIGH (affects all agents), MEDIUM (domain-specific), LOW (task-specific).
3. User approves batch promotion to instructions, workflows, or skills via `/promote-learning`.
4. Promoted entries are archived to `learning-archive-YYYY-MM.md` and removed from the source file.

---

## Format Converters

Converter templates in `converters/` define how to transform PATTERNS/ERRORS entries into their target format. The orchestrator uses these when generating the Learning Promotion Report.

| Converter                                                          | Input             | Output                                                           |
| ------------------------------------------------------------------ | ----------------- | ---------------------------------------------------------------- |
| [patterns-to-instructions](converters/patterns-to-instructions.md) | PATTERNS.md entry | `.github/instructions/*.instructions.md`                         |
| [patterns-to-workflow](converters/patterns-to-workflow.md)         | PATTERNS.md entry | `.github/workflows/*.workflow.md`                                |
| [patterns-to-skill](converters/patterns-to-skill.md)               | PATTERNS.md entry | `.github/skills/*/SKILL.md`                                      |
| [errors-to-instructions](converters/errors-to-instructions.md)     | ERRORS.md entry   | `.github/instructions/*.instructions.md` troubleshooting section |

**Duplicate detection**: Before any insertion, check the target file for similar entries (~70% keyword overlap). Flag as `DUPLICATE_CANDIDATE` and surface to user — never auto-insert duplicates.

**Cross-reference preservation**: All inserted content includes a `<!-- Source: PATTERNS.md #[ID] -->` comment so the instruction's origin can be traced back. 5. Use `/cleanup-learning` to archive unpromoted task-specific entries after each story/epic.
