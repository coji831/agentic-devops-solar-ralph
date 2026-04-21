# SOLAR Patterns

Implementation patterns extracted from multi-iteration struggles: non-obvious
solutions, project gotchas, architectural decisions validated under pressure, and
conventions confirmed through 2+ rework cycles. Injected as condensed `additionalContext`
by the `SessionStart` hook.

## How to Use

After completing a task that required 2+ rework cycles or a non-obvious solution,
add an entry using the format:

```
### [DATE] [CATEGORY] — [SHORT TITLE]
**Problem:** <what went wrong or was unclear>
**Solution:** <how it was resolved>
**Lesson:** <the reusable rule or pattern to apply next time>
```

Categories: `convention`, `architecture`, `tooling`, `pattern`, `gotcha`, `security`

The `SessionStart` hook reads this file and injects a condensed summary (up to 20
non-header lines) into each session's context so agents benefit from accumulated
knowledge without manual re-reading.

---

<!-- Entries appear below this line -->
