# Subagent Isolation and Handoff Patterns

**One-sentence summary**: VS Code subagents run in fully isolated context windows — the key to low token usage is what you pass _in_ (dispatch prompt) and what comes _back_ (return message), not the isolation itself.

---

## When to Use

- Any multi-agent pipeline where a specialist does significant file reading
- Any task where a previous agent's research should NOT contaminate the next agent's context
- Any pipeline with a Data Collector or Bug Investigation stage that reads 5+ files

## When NOT to Use

- Simple single-file fixes — subagent overhead isn't worth it
- Tasks where the governor genuinely needs the full findings inline (very rare)

---

## Context Isolation: What VS Code Actually Does

Official VS Code docs (2026):

> _"Context isolation: each subagent runs in its own context window. It doesn't inherit the main agent's conversation history or instructions. It receives only the task prompt."_

> _"Only the final result is returned to the main agent, keeping the main context focused and reducing token usage."_

**What this means in practice:**

- A subagent that calls `read_file` 20 times does NOT add those 20 results to the parent conversation
- Only the subagent's _return message_ appends to the parent conversation
- If the return message contains 8,000 tokens of raw file content — those 8,000 tokens DO accumulate in the parent

**The real bottleneck is the return message, not the isolation.**

---

## The Three Rules

### Rule 1 — Minimal Dispatch Prompt

The governor's runSubagent prompt must contain ONLY:

1. Task description (2–3 sentences)
2. Schema type + input file path from `## Materials`
3. Result file path to write to (`verification-artifacts/{task-id}-{stage}-result.json`)
4. Return format instruction (verbatim, see below)

```
Task: Collect files related to the authentication middleware.
Input schema: scout_findings. Input path: (none — perform fresh search)
Result path: verification-artifacts/20260506-auth-bug-scan.json
Return format: "Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."
```

**Never embed raw file contents or ledger history in the dispatch prompt.** The subagent reads files in its own isolated context.

### Rule 2 — Condensed Return Message

Every specialist must return EXACTLY this format:

```
{status}. Result: {file-path}. Summary: {2 sentences describing top findings, no raw content}.
```

Example:

```
COMPLETED. Result: verification-artifacts/20260506-auth-bug-scan.json. Summary: Found improper JWT validation in auth-middleware.ts lines 45-67. Three routes lack the requireAuth guard — /api/admin, /api/users/:id, /api/settings.
```

### Rule 3 — Governor is Index Only

The governor manages the `## Materials` table as a **lightweight index**:

- Tracks: file path, schema type, status (`pending` | `ready` | `reviewed`)
- Does NOT read the contents of result files
- Does NOT embed file contents in subsequent dispatch prompts

Next specialist gets: "Read `verification-artifacts/20260506-auth-bug-scan.json` (schema: scout_findings)." Not: the full file contents copied in.

---

## Handoff File Protocol

### Files Produced

| Stage          | File                                                       | Schema            |
| -------------- | ---------------------------------------------------------- | ----------------- |
| Scan           | `verification-artifacts/{id}-scan.json`                    | `scout_findings`  |
| Design         | `verification-artifacts/{id}-design.json`                  | `designer_output` |
| Implement      | `verification-artifacts/{id}-impl.json`                    | `dev_progress`    |
| Test           | `verification-artifacts/{id}-test.json`                    | `qa_result`       |
| Review         | `verification-artifacts/{id}-verify.json`                  | `review_result`   |
| Ledger archive | `verification-artifacts/{YYYYMMDD}-{id}-ledger-archive.md` | —                 |

Schemas live in `.github/solar-system/schemas/`.

### Ledger Materials Table

```markdown
## Materials

| role   | path                                           | schema         | status |
| ------ | ---------------------------------------------- | -------------- | ------ |
| input  | verification-artifacts/20260506-auth-scan.json | scout_findings | ready  |
| output | verification-artifacts/20260506-auth-impl.json | dev_progress   | empty  |
```

Governor updates this table before and after each dispatch — it is the only place it stores inter-stage state.

---

## Ledger Reset/Archive Protocol

After every WORK_PACKAGE_COMPLETE / TASK_COMPLETE:

1. **Archive**: `create_file` → `verification-artifacts/{YYYYMMDD}-{task-id}-ledger-archive.md` with current ledger content
2. **Reset**: Read the Ledger Template block from `.github/AGENTS.md` Section 7 and overwrite `.github/.ai_ledger.md` with that content

This ensures each new task starts from a clean ledger with no stale pipeline state, stale materials rows, or stale decisions log entries.

---

## Token Impact

From telemetry analysis (SOLAR v4.6, May 2026):

| Source                    | Tokens (pre-fix) | Tokens (post-fix)             |
| ------------------------- | ---------------- | ----------------------------- |
| read_file accumulation    | ~59,051 (55%)    | ~0 (subagent isolated)        |
| Subagent return messages  | ~2,000           | ~500 (condensed return)       |
| Governor dispatch prompts | ~3,000           | ~300 (paths only, no content) |

Expected token reduction: 50–65% on context size at equivalent pipeline depth.

---

## Common Mistakes

| Mistake                                           | Symptom                                  | Fix                                 |
| ------------------------------------------------- | ---------------------------------------- | ----------------------------------- |
| Governor embeds file content in dispatch prompt   | High token usage at each stage           | Pass file paths only, not contents  |
| Specialist returns raw file content               | Parent context grows 10K+ per specialist | Enforce condensed return format     |
| Governor reads specialist result files "to check" | Defeats the isolation benefit            | Governor reads Materials index only |
| New task starts without ledger reset              | Stale pipeline stage + materials rows    | Archive + reset at TASK_COMPLETE    |

---

## Related

- [v4-artifact-handle-pattern.md](v4-artifact-handle-pattern.md) — threshold rules for full load vs. path handle
- [v4-context-tiers.md](v4-context-tiers.md) — context tier budget model
- [v4-handoff-types-catalog.md](v4-handoff-types-catalog.md) — schema definitions for all handoff types
- [agent-memory-governance.md](agent-memory-governance.md) — memory scopes and governance
