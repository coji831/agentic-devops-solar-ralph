# Converter: ERRORS.md → Instructions File (Troubleshooting Section)

Transforms an ERRORS.md entry into a troubleshooting addition for the relevant `.github/instructions/*.instructions.md` file.

## When to Use

Use when an ERRORS.md entry describes a **platform workaround, tool limitation, or error recovery pattern** that all agents in a domain should know about before attempting the same approach.

- HIGH: Affects all agents on all projects → `conventions.instructions.md`
- MEDIUM: Tool-specific or domain-specific → `frontend.instructions.md`, `backend.instructions.md`, etc.
- LOW: Project-specific quirk → `architecture.instructions.md`

## Input: ERRORS.md Entry Format

```
### [DATE] [TOOL NAME] — [SHORT DESCRIPTION]
**Error**: <what happened>
**Context**: <what you were doing when it occurred>
**Workaround**: <what worked instead>
```

## Output: Instructions File Addition

Add to a `## Known Tool Limitations` or `## Troubleshooting` section in the target instructions file. Create the section if it doesn't exist.

```markdown
<!-- Source: ERRORS.md #[DATE]-[TOOL-NAME] -->
### [Tool Name]: [Short Description]

**Symptom**: [Observable failure — what the agent sees when this problem occurs]

**Trigger**: [What action or context causes this error]

**Workaround**: [Exact alternative to use instead]

**Do NOT**: [The approach that caused the error — clearly state what to avoid]

**Verified date**: [DATE from the ERRORS.md entry]
```

## Duplicate Detection

Before inserting, search the target instructions file's troubleshooting section for:
- Tool name matches
- Symptom descriptions with overlapping failure modes

If overlap exists: update the existing entry rather than adding a new one. Note the additional occurrence date in a comment: `<!-- Also observed: [DATE] -->`.

## Placement Rules

- Add to `## Known Tool Limitations` or `## Troubleshooting` section
- If no such section exists: add at the **end** of the target instructions file with the appropriate heading
- Group by tool name if multiple entries exist for the same tool
- Most recently verified entries should appear first within a tool group

## Example Transformation

**Input (ERRORS.md):**
```
### 2026-04-02 semantic_search — 7-Minute Hang in Subagent Environments
**Error**: semantic_search hung for 7 minutes with no output in a subagent invocation.
**Context**: Attempting to find all usages of a hook across the codebase.
**Workaround**: Used grep_search with a regex pattern instead — completed in <5 seconds.
```

**Output (conventions.instructions.md addition):**
```markdown
<!-- Source: ERRORS.md #2026-04-02-semantic_search -->
### semantic_search: 7-Minute Hang in Subagent Environments

**Symptom**: Tool call produces no output for 7+ minutes, blocking the entire subagent context window.

**Trigger**: Using `semantic_search` in any subagent invocation (runSubagent context).

**Workaround**: Use `grep_search` with a regex pattern for the specific symbol or concept. Use `file_search` for path-based lookups.

**Do NOT**: Use `semantic_search` in subagent environments.

**Verified date**: 2026-04-02
```
