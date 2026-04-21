# Converter: PATTERNS.md → Instructions File

Transforms a PATTERNS.md entry into a formatted addition for `.github/instructions/*.instructions.md`.

## When to Use

Use when the pattern entry classification is **HIGH** (applies to all agents) or **MEDIUM** (applies to a specific domain).

- HIGH → `conventions.instructions.md` or `workflow.instructions.md`
- MEDIUM/frontend → `frontend.instructions.md`
- MEDIUM/backend → `backend.instructions.md`
- MEDIUM/docs → (Docs Curator guidance section)

## Input: PATTERNS.md Entry Format

```
### [DATE] [CATEGORY] — [SHORT TITLE]
**Problem**: <what was difficult or required rework>
**Solution**: <approach that resolved it>
**Lesson**: <one-sentence takeaway>
```

## Output: Instructions File Addition

Place the converted content in the appropriate section of the target instructions file. Use the following format:

```markdown
<!-- Source: PATTERNS.md #[DATE]-[SHORT-TITLE] -->

### [Short descriptive rule title]

**Context**: [When this rule applies — e.g., "When implementing backend routes", "When designing frontend state"]

**Rule**: [The actionable convention or guideline derived from the lesson. Written as a directive, not a narrative.]

**Rationale**: [One sentence explaining why — derived from the Problem field of the source entry.]

**Example** (if applicable):
\`\`\`
[Code or command example showing the correct pattern]
\`\`\`
```

## Duplicate Detection

Before inserting, search the target instructions file for:

- The main keyword from the entry title
- The core concept from the Lesson field

If either matches an existing entry within ~70% similarity: flag as `DUPLICATE_CANDIDATE` and surface to user. Do not auto-insert.

## Placement Rules

- Add to the **most specific applicable section** in the target file
- If no matching section exists: add a new section heading at the bottom of the file
- Do not modify existing rules — only add new ones
- After insertion, Docs Curator must verify template compliance for the instructions file

## Example Transformation

**Input (PATTERNS.md):**

```
### 2026-04-15 BACKEND — Prisma Migration Order Matters
**Problem**: Running migrations before seeding caused FK constraint failures in test setup.
**Solution**: Always run migrate-deploy before seed in test setup scripts.
**Lesson**: Migration order must be documented in test setup conventions.
```

**Output (backend.instructions.md addition):**

```markdown
<!-- Source: PATTERNS.md #2026-04-15-Prisma-Migration-Order-Matters -->

### Prisma Test Setup Order

**Context**: When setting up backend test environments with Prisma.

**Rule**: Always run `prisma migrate deploy` before `prisma db seed` in test setup. Never reverse this order.

**Rationale**: Running seed before migrate causes FK constraint failures because referenced tables may not exist yet.
```
