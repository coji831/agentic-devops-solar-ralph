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
5. Use `/cleanup-learning` to archive unpromoted task-specific entries after each story/epic.
